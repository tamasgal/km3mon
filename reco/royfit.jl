#!/usr/bin/env julia
println("Initialising libraries, this may take a minute...")
using Sockets
using NeRCA
using Plots
using PlotThemes
using Dates
using Measures
GR.inline("png")

if length(ARGS) < 2
    println("Usage: ./live_royfit.jl LIGIER_HOST LIGIER_PORT")
    exit(1)
end


const calib = NeRCA.read_calibration("/data/latest.detx")
const LIGIER_HOST = getalladdrinfo(ARGS[1])[1]
const LIGIER_PORT = parse(Int, ARGS[2])
const DOWNSAMPLE = 0.5  # fraction to keep

function main()
    println("Starting live ROyFit")

    sparams = NeRCA.SingleDURecoParams()

    for (idx, message) in enumerate(CHClient(LIGIER_HOST, LIGIER_PORT, ["IO_EVT"]))

	idx % 80 == 0 && println()

        if rand() > DOWNSAMPLE
            print(".")
            continue
        end
        event = NeRCA.read(IOBuffer(message.data), NeRCA.DAQEvent)

        hits = calibrate(calib, event.hits)
        triggered_hits = triggered(hits)
        dus = sort(unique(map(h->h.du, hits)))
        triggered_dus = sort(unique(map(h->h.du, triggered_hits)))
        n_dus = length(dus)
        n_triggered_dus = length(triggered_dus)
        n_doms = length(unique(h->h.dom_id, triggered_hits))

        if n_doms < 4
            print("s")
            continue
        end
        print("R")

        colours = palette(:default)
        plot()
        Q = []
        for (idx, du) in enumerate(dus)
            du_hits = filter(h->h.du == du, hits)
            if length(triggered(du_hits))== 0
                continue
            end
            fit = NeRCA.single_du_fit(du_hits, sparams)
            push!(Q, fit.Q)
            plot!(du_hits, fit, markercolor=colours[idx], label="DU $(du)", max_z=calib.max_z)
            write_time_residuals("/data/reco_timeres.csv", event, fit.selected_hits, fit)
        end
        if sum(Q) < 200 && n_doms > 9 && n_dus > 1
            fit_params = "ROy live reconstruction (combined single line): Q=$([round(_Q,digits=2) for _Q in Q])"
            event_params = "Det ID $(event.det_id), Run $(event.run_id), FrameIndex $(event.timeslice_id), TriggerCounter $(event.trigger_counter), Overlays $(event.overlays)"
            time_params = "$(unix2datetime(event.timestamp)) UTC"
            trigger_params = "Trigger: $(is_mxshower(event) ? "MX " : "")$(is_3dmuon(event) ? "3DM " : "")$(is_3dshower(event) ? "3DS " : "")"
            time_params = "$(unix2datetime(event.timestamp)) UTC"

            plot!(title="$(fit_params)\n$(event_params), $(trigger_params)\n$(time_params)", titlefontsize=8, margin=5mm)

            savefig("/plots/ztplot_roy.png")

            print("+")
        end

        #= if n_triggered_dus > 2 && n_doms > 14 =#
        #=     selected_hits = unique(h->h.dom_id, triggered_hits) =#
        #=     println("\nStarting multiline fit with $(n_dus) DUs and $(length(selected_hits)) selected hits") =#
        #=     prefit_track = NeRCA.prefit(selected_hits) =#
        #=     println(prefit_track) =#
        #=     plot(selected_hits, prefit_track) =#
        #=     savefig("plots/ztplot_roy_prefit.png") =#
        #= end =#
    end
end

function write_time_residuals(filename, event, hits, fit)
    if !isfile(filename)
        fobj = open(filename, "w")
        write(fobj, "run,timestamp,du,floor,dom_id,t_res,Q\n")
    else
        fobj = open(filename, "a")
    end
    dγ, ccalc = NeRCA.make_cherenkov_calculator(fit.sdp)
    for hit in hits
        Δt = hit.t - ccalc(hit.pos.z)
        write(fobj, "$(event.run_id),$(event.timestamp),$(hit.du),$(hit.floor),$(hit.dom_id),$(Δt),$(fit.Q)\n")
    end
    close(fobj)
end

main()
