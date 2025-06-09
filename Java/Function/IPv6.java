import java.net.InetAddress;
import java.net.UnknownHostException;
import java.nio.charset.StandardCharsets;

public class IPv6 {
    // EX) FD01:100:1::8745:1107 -> [56, 55, 52, 53, 49, 49, 48, 55] (represents UTF-8 bytes of "87451107")
    protected static byte[] IPv6_Part_PhoneNumber(InetAddress IPv6Address) {
        if (IPv6Address == null) {
            throw new IllegalArgumentException("[Error] IPv6 Address is null.");
        }

        String IPv6Address_String = IPv6Address.getHostAddress();

        if (!IPv6Address_String.contains(":")) {
            throw new IllegalArgumentException("[Error] Invalid IPv6 Address.");
        }

        String[] parts = IPv6Address_String.split(":");
        if (parts.length < 3) {
            throw new IllegalArgumentException("[Error] IPv6 Address Format Error.");
        }

        String firstSegment = parts[parts.length - 2].replaceAll("[^0-9]", "").trim();
        String secondSegment = parts[parts.length - 1].replaceAll("[^0-9]", "").trim();

        if (firstSegment.isEmpty()) {
            firstSegment = "0";
        }
        if (secondSegment.isEmpty()) {
            secondSegment = "0";
        }

        String firstSegmentNumbers = String.format("%04d", Integer.parseInt(firstSegment));
        String secondSegmentNumbers = String.format("%04d", Integer.parseInt(secondSegment));

        return (firstSegmentNumbers + secondSegmentNumbers).getBytes(StandardCharsets.UTF_8);
    }

    // EX) "fd01:100:1:0:0:0:8745:1107" -> [0xfd, 0x01, 0x01, 0x00, ..., 0x87, 0x45, 0x11, 0x07]
    protected static byte[] IPv6_String_to_IPv6_Bytearray(String IPv6_String) {
        byte[] IPv6_Bytearray = new byte[16];
        String[] parts = IPv6_String.split(":");
        for (int i = 0; i < parts.length; i++) {
            int value = Integer.parseInt(parts[i], 16);
            IPv6_Bytearray[i * 2] = (byte) (value >> 8);
            IPv6_Bytearray[i * 2 + 1] = (byte) value;
        }
        return IPv6_Bytearray;
    }

    // EX) [0xfd, 0x01, 0x01, 0x00, ..., 0x87, 0x45, 0x11, 0x07] -> "fd01:100:1::8745:1107"
    protected static String IPv6_Bytearray_to_IPv6(byte[] IPv6_Bytearray) {
        try {
            InetAddress inetAddress = InetAddress.getByAddress(IPv6_Bytearray);
            return inetAddress.getHostAddress().replaceAll(":(0:)+", "::").replaceAll(":::", "::");
        } catch (UnknownHostException e) {
            throw new RuntimeException("[Error] IPv6_Bytearray_to_IPv6 Error", e);
        }
    }

    // EX) "fd01:100:1:0:0:0:8745:1107" -> "fd01:100:1::8745:1107"
    protected static String IPv6_String_to_IPv6(String IPv6_String) {
        try {
            InetAddress inetAddress = InetAddress.getByName(IPv6_String);
            return inetAddress.getHostAddress().replaceAll(":(0:)+", "::").replaceAll(":::", "::");
        } catch (UnknownHostException e) {
            throw new RuntimeException("[Error] IPv6_String_to_IPv6 Error", e);
        }
    }

    // EX) [0xc0, 0xa8, 0x01, 0x01] -> "192.168.1.1"
    protected static String IPv4_Bytearray_to_IPv4_String(byte[] IPv4_Bytearray) {
        try {
            InetAddress IPv4_Address = InetAddress.getByAddress(IPv4_Bytearray);
            return IPv4_Address.getHostAddress();
        } catch (UnknownHostException e) {
            throw new RuntimeException("[Error] IPv4_Bytearray_to_IPv4_String Error", e);
        }
    }
}
