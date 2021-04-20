#include <chrono>
#include <iostream>
#include <set>
#include <string>

#include "Jeep/JParser.hh"
#include "Jeep/JMessage.hh"
#include "JNet/JControlHost.hh"
#include "JSystem/JDate.hh"


/**
 * \file
 *
 * A tool to forward messages with the given tags from one ControlHost server (e.g. JLigier) to another.
 *
 * The options <tt>-H \<source\>[:port]</tt> and <tt>-H \<target\>[:port]</tt>
 * correponds to the hostname and the port of the source and target server, respectively.
 * The options <tt>-t</tt> and <tt>-T</tt> correspond to the ControlHost tag(s)
 * with the mode subscription "any" and subscription "all".
 * \author tgal
 */
int main(int argc, const char *argv[])
{
  using namespace std;

  string          source;
  string          target;
  int             report_interval;  // in seconds
  set<JNET::JTag> tagList;
  set<JNET::JTag> TagList;
  int             debug;

  try {

    JParser<> zap("Program to forward messages from one ControlHost server to another.");

    zap['H'] = make_field(source)          = "localhost";
    zap['X'] = make_field(target)          = "localhost";
    zap['t'] = make_field(tagList);
    zap['T'] = make_field(TagList);
    zap['i'] = make_field(report_interval) = 30;
    zap['d'] = make_field(debug)           = 0;

    zap['t'] = JPARSER::initialised();
    zap['T'] = JPARSER::initialised();

    zap(argc, argv);
  }
  catch(const exception &error) {
    FATAL(error.what() << endl);
  }


  if (tagList.empty() && TagList.empty()) {
    FATAL("No tags specified.");
  }

  using namespace JPP;

  cout << "Forwarding messages from " << endl << "    " << source << " -> " << target << endl;


  JControlHost::Throw(true);

  try {

    JControlHost in(source);
    JControlHost out(target);

    cout << "with the following tags: ";

    {
      JSubscriptionList buffer;

      for (set<JTag>::const_iterator i = tagList.begin(); i != tagList.end(); ++i) {
        buffer.add(JSubscriptionAny(*i));
        cout << *i << "(any) ";
      }

      for (set<JTag>::const_iterator i = TagList.begin(); i != TagList.end(); ++i) {
        buffer.add(JSubscriptionAll(*i));
        cout << *i << "(all) ";
      }

      cout << endl;

      in.Subscribe(buffer);
      in.SendMeAlways();
    }


    JPrefix      prefix;
    vector<char> buffer;
    unsigned int message_count = 0;
    float        milliseconds_passed;
    std::chrono::high_resolution_clock::time_point start_time = std::chrono::high_resolution_clock::now();

    for (const string stop("stop"); buffer.size() != stop.size() || string(buffer.data(), stop.size()) != stop; ) {

      in.WaitHead(prefix);

      buffer.resize(prefix.getSize());

      in.GetFullData(buffer.data(), buffer.size());

      DEBUG(getDateAndTime() << ' ' << left << setw(8) << prefix.getTag() << ' ' << right << setw(8) << prefix.getSize() << endl);

      out.PutFullData(prefix.getTag(), buffer.data(), buffer.size());

      message_count += 1;
      milliseconds_passed = (std::chrono::high_resolution_clock::now() - start_time) / std::chrono::milliseconds(1);

      if(milliseconds_passed > report_interval * 1e3) {
          cout << getDateAndTime() << " : " << "Message rate: " << message_count / milliseconds_passed * 1e3 << " Hz" << endl;
          start_time = std::chrono::high_resolution_clock::now();
          message_count = 0;
      }
    }
  }
  catch(const JControlHostException& error) {
    ERROR(error << endl);
  }
}
