#!/bin/zsh
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideLastUpdated>true</swiftbar.hideLastUpdated>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>
# Menu bar toggle for the awake command-line tool. Refreshes every 5 seconds.
# @AWAKE@ is filled in with the real path by: ./install.sh --menubar
A="@AWAKE@"
st=$("$A" status 2>&1)
if [[ $st == ON* ]]; then echo "☕"; else echo "💤"; fi
echo "---"
echo "$st"
echo "---"
if [[ $st == ON* ]]; then
  echo "Turn off | shell=$A param1=off terminal=false refresh=true"
else
  [[ $st == *stale* ]] && echo "Restore screen saver setting | shell=$A param1=off terminal=false refresh=true"
  echo "Keep awake (until I turn it off) | shell=$A param1=on terminal=false refresh=true"
  echo "Keep awake for 30 minutes | shell=$A param1=on param2=30m terminal=false refresh=true"
  echo "Keep awake for 1 hour | shell=$A param1=on param2=1h terminal=false refresh=true"
  echo "Keep awake for 2 hours | shell=$A param1=on param2=2h terminal=false refresh=true"
fi
