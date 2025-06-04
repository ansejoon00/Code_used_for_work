import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class Print_Packet {
    protected static void printf_byte(String label, byte array, int start_index, int size) {
        if (Server.Debug) {
            System.out.println("  [" + label + "] " + "[" + size + "]");
            System.out.printf("     %02X\n", array);
        }
    }

    protected static void printf_byte(String label, byte[] array, int start_index, int size) {
        if (Server.Debug) {
            System.out.print("  [" + label + "] " + "[" + size + "]");

            for (int i = 0; i < size; i++) {
                if (i % 25 == 0) {
                    System.out.print("\n    ");
                }
                System.out.printf(" %02X", array[start_index + i]);
            }
            System.out.println();
        }
    }

    protected static void printf_byte_s(String label, byte[] array, int start_index, int size) {
        System.out.print("  [" + label + "] " + "[" + size + "]");

        for (int i = 0; i < size; i++) {
            if (i % 25 == 0) {
                System.out.print("\n    ");
            }
            System.out.printf(" %02X", array[start_index + i]);
        }
        System.out.println();
    }

    private static final DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSSSSSSSS");

    private static String get_Formatted_Time() {
        return LocalDateTime.now().format(formatter);
    }

    protected static void printf_Packet(String type, Modem_INFO modem_info, char cmd, boolean result, byte[] packet) {
        String time = get_Formatted_Time();
        if (result) {
            System.out.println("[" + type + " Packet] " + type + " Success CMD: " + cmd + " / Time : " + time);
        } else {
            System.out.println("==================================================================================");
            System.out.println("                                       " + type);
            printf_modem_info(modem_info);
            System.out.println("[" + type + " Packet] " + type + " CMD : " + cmd + " / Time : " + time);
            System.out.println("[" + type + " Packet Data Size] : " + packet.length + " / Time : " + time);
            printf_byte_s(type + " Packet Data", packet, 0, packet.length);
        }
    }

    protected static void printf_modem_info(Modem_INFO modem_info) {
        System.out.println("[Modem INFO]");
        System.out.println("  - DCU ID         : " + modem_info.DCU_ID);
        System.out.println("  - Modem SysT     : " + Convert.hex_to_system_title(modem_info.modem_SysT));
        System.out.println("  - Modem FEP Key  : " + modem_info.modem_Fep_Key);
        System.out.println("  - Modem IP       : " + IPv6.IPv6_String_to_IPv6(modem_info.modem_IP));
    }
}
