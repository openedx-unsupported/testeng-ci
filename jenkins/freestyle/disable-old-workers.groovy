// This script is built for the script console in Jenkins

import hudson.model.*
import hudson.node_monitors.*
import hudson.slaves.*
import java.util.concurrent.*

import hudson.model.*;

jenkins = Hudson.instance

for (slave in jenkins.computers) {
  def computer = slave.name
// change the name string according to your needs
    if (slave.name.contains("jenkins-worker") {
      println(slave.name)
// the line below is commented out by default, but will set
// the given worker offline, and assign the string as its
// offline reason
//        slave.cliOffline("old worker")
}
}
