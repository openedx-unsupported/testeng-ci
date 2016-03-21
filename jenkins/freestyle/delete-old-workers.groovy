import hudson.model.*
import hudson.node_monitors.*
import hudson.slaves.*
import java.util.concurrent.*

jenkins = Hudson.instance

for (slave in jenkins.computers) {
    def computer = slave.name
    if (slave.name != "master" & slave.isOffline() & slave.offlineCause != null) {
        offCause = slave.getOfflineCause().toString()
        if (offCause.contains("Time out for last 5 try")) {
            println("Deleting " + slave.name + " which has the status: " + slave.offlineCause)
            slave.doDoDelete()
        }
    }
}
