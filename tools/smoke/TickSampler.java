import javax.management.MBeanServerConnection;
import javax.management.ObjectName;
import javax.management.remote.JMXConnector;
import javax.management.remote.JMXConnectorFactory;
import javax.management.remote.JMXServiceURL;

/**
 * The duration of every server tick, read from the dedicated server's own JMX bean (server.properties
 * enable-jmx-monitoring=true: net.minecraft.server:type=Server, attribute tickTimes = the last 100 tick durations in ns,
 * a ring indexed by the tick count). It is polled from outside the game every POLL_MS (about 5 ticks at 20 TPS, far from
 * the 100 the ring keeps): the slots that changed since the last poll are the new ticks. Nothing runs inside the game,
 * so it works the same with and without Heraldia (the vanilla server has no mod to ask).
 *
 * Usage (single-file source, Java 25): java tools/smoke/TickSampler.java PORT SECONDS
 * Prints one line per tick, its duration in ns, and at the end "# polls N lost L" (L > 0: a poll came more than 100 ticks
 * after the previous one, so some ticks were not seen). Used by tools/smoke/runtime_cost.py.
 */
public final class TickSampler {
	private static final long POLL_MS = 250;

	public static void main(String[] args) throws Exception {
		int port = Integer.parseInt(args[0]);
		long until = System.nanoTime() + (long) (Double.parseDouble(args[1]) * 1e9);
		JMXServiceURL url = new JMXServiceURL("service:jmx:rmi:///jndi/rmi://127.0.0.1:" + port + "/jmxrmi");
		try (JMXConnector c = JMXConnectorFactory.connect(url)) {
			MBeanServerConnection m = c.getMBeanServerConnection();
			ObjectName server = new ObjectName("net.minecraft.server:type=Server");
			long[] prev = (long[]) m.getAttribute(server, "tickTimes");
			int polls = 0, lost = 0;
			StringBuilder out = new StringBuilder();
			while (System.nanoTime() < until) {
				Thread.sleep(POLL_MS);
				long[] cur = (long[]) m.getAttribute(server, "tickTimes");
				int changed = 0;
				for (int i = 0; i < cur.length; i++) {
					if (cur[i] != prev[i]) {
						out.append(cur[i]).append('\n');
						changed++;
					}
				}
				if (changed == cur.length) {
					lost++;     // every slot changed: the ring may have wrapped around between two polls
				}
				prev = cur;
				polls++;
			}
			out.append("# polls ").append(polls).append(" lost ").append(lost).append('\n');
			System.out.print(out);
		}
	}
}
