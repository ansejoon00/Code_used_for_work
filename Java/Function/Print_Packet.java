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

    protected static void printf_Send_packet(byte[] packet) {
        System.out.println("[Send Packet Data Size] : " + packet.length);
        Print_Packet.printf_byte_s("Send Packet Data", packet, 0, packet.length);
    }

    protected static void printf_Trap_packet(byte[] packet) {
        System.out.println("[Trap Packet Data Size] : " + packet.length);
        Print_Packet.printf_byte_s("Trap Packet Data", packet, 0, packet.length);
    }

    protected static void printf_Recv_packet(byte[] packet) {
        System.out.println("[Recv Packet Data Size] : " + packet.length);
        Print_Packet.printf_byte_s("Recv Packet Data", packet, 0, packet.length);
    }
}
