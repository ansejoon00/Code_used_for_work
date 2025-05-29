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

    protected static void printf_Send_cmd(char cmd, boolean result) {
        String time = get_Formatted_Time();
        if (result) {
            System.out.println("[Send Packet] Send Success CMD: " + cmd + " / Time : " + time);
        } else {
            System.out.println("==================================================================================");
            System.out.println("[Send Packet] Send CMD : " + cmd + " /  Time : " + time);
        }
    }

    protected static void printf_Send_packet(byte[] packet) {
        String time = get_Formatted_Time();
        System.out.println("[Send Packet Data Size] : " + packet.length + " / Time : " + time);
        printf_byte_s("Send Packet Data", packet, 0, packet.length);
    }

    protected static void printf_Trap_cmd(char cmd, boolean result) {
        String time = get_Formatted_Time();
        if (result) {
            System.out.println("[Trap Packet] Trap Success CMD: " + cmd + " / Trap Time : " + time);
        } else {
            System.out.println("==================================================================================");
            System.out.println("[Trap Packet] Trap CMD : " + cmd + " / Trap Time : " + time);
        }
    }

    protected static void printf_Trap_packet(byte[] packet) {
        String time = get_Formatted_Time();
        System.out.println("[Trap Packet Data Size] : " + packet.length + " / Time : " + time);
        printf_byte_s("Trap Packet Data", packet, 0, packet.length);
    }

    protected static void printf_Recv_cmd(char cmd, boolean result) {
        String time = get_Formatted_Time();
        if (result) {
            System.out.println("[Recv Packet] Recv Success CMD: " + cmd + " / Recv Time : " + time);
        } else {
            System.out.println("==================================================================================");
            System.out.println("[Recv Packet] Recv CMD : " + cmd + " / Recv Time : " + time);
        }
    }

    protected static void printf_Recv_packet(byte[] packet) {
        String time = get_Formatted_Time();
        System.out.println("[Recv Packet Data Size] : " + packet.length + " / Time : " + time);
        printf_byte_s("Recv Packet Data", packet, 0, packet.length);
    }
}
