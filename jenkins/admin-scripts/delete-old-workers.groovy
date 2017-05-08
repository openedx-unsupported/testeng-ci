import hudson.model.*
import hudson.node_monitors.*
import hudson.slaves.*
import java.util.concurrent.*

jenkins = Hudson.instance

for (slave in jenkins.computers) {
    def computer = slave.name
    // filter for workers that are offline, are not processing anything, and have some description on why
    // they are offline
    if (slave.name != "master" & slave.isOffline() & slave.offlineCause != null & slave.countBusy() == 0) {
        offCause = slave.getOfflineCause().toString()
        // another filter for a specific offline reason.
        if (offCause.contains("Time out for last 5 try")) {
            println("Deleting " + slave.name + " which has the status: " + slave.offlineCause)
            slave.doDoDelete()
        }
    }
}
