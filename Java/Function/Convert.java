import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;

public class Convert {
    // byte test = (byte) 0x31;
    // >> "31"
    protected static String hexByte_To_HexString(byte hex, int len) {
        String result = Integer.toHexString((hex >> 4) & 0x0F) + Integer.toHexString(hex & 0x0F);

        return result;
    }

    // byte test[] = { (byte) 0x31, (byte) 0x32, (byte) 0x33, (byte) 0xAB, (byte) 0xCD };
    // >> "313233ABCD"
    protected static String hexByte_To_HexString(byte[] hexArray, int len) {
        StringBuilder result = new StringBuilder();

        for (int i = 0; i < len; i++) {
            result.append(Integer.toHexString((hexArray[i] >> 4) & 0x0F));
            result.append(Integer.toHexString(hexArray[i] & 0x0F));
        }
        return result.toString();
    }

    // byte test[] = { (byte) 0x31, (byte) 0x32, (byte) 0x33, (byte) 0x41, (byte) 0x42 };
    // >> "123AB"
    protected static String hexByte_To_String(byte[] hexArray, int len) {
        StringBuilder result = new StringBuilder();
        for (int i = 0; i < len; i++) {
            result.append((char) hexArray[i]);
        }
        return result.toString();
    }

    // String test = "3132333435";
    // >> { (byte) 0x31, (byte) 0x32, (byte) 0x33, (byte) 0x34, (byte) 0x35 };
    protected static byte[] hexString_To_ByteArray(String hex) {
        int len = hex.length();
        byte[] data = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            data[i / 2] = (byte) ((Character.digit(hex.charAt(i), 16) << 4) + Character.digit(hex.charAt(i + 1), 16));
        }
        return data;
    }

    // String test = "12345";
    // >> { (byte) 0x31, (byte) 0x32, (byte) 0x33, (byte) 0x34, (byte) 0x35 };
    protected static byte[] String_To_ByteArray(String input, int len) {
        byte[] bytes = new byte[len];
        if (input != null) {
            byte[] inputBytes = input.getBytes(StandardCharsets.UTF_8);
            System.arraycopy(inputBytes, 0, bytes, 0, Math.min(inputBytes.length, len));
        }
        return bytes;
    }

    // String test = "313233";
    // >> 123
    protected static String ascii_To_Plaintext(String asciiString) {
        int len = asciiString.length();
        StringBuilder plaintext = new StringBuilder();

        for (int i = 0; i < len; i += 2) {
            String hexByte = asciiString.substring(i, i + 2);
            plaintext.append((char) Integer.parseInt(hexByte, 16));
        }

        return plaintext.toString();
    }

    // value = 60, len = 2
    // >> { (byte) 0x00, (byte)0x3C }
    protected static byte[] int_To_ByteArray(int value, int len) {
        ByteBuffer buffer = ByteBuffer.allocate(len);

        if (len == 1) {
            buffer.put((byte) value);
        } else if (len == 2) {
            buffer.putShort((short) value);
        } else if (len == 4) {
            buffer.putInt(value);
        }
        return buffer.array();
    }

    // value = 60, len = 2
    // >> { (byte) 0x3C, (byte) 0x00 }
    protected static byte[] int_To_ByteArray_LE(int value, int len) {
        ByteBuffer buffer = ByteBuffer.allocate(len);
        buffer.order(ByteOrder.LITTLE_ENDIAN);

        if (len == 1) {
            buffer.put((byte) value);
        } else if (len == 2) {
            buffer.putShort((short) value);
        } else if (len == 4) {
            buffer.putInt(value);
        }
        return buffer.array();
    }

    // bytearray = { (byte) 0x00, (byte)0x3C }, len = 2
    // >> 60
    protected static int convertByte_To_int(byte[] bytearray, int len) {
        ByteBuffer buffer = ByteBuffer.wrap(bytearray);
        if (len == 2) {
            return buffer.getShort() & 0xFFFF;
        }
        if (len == 4) {
            return buffer.getInt();
        } else {
            return 0;
        }
    }

    // bytearray = { (byte)0x3C, (byte) 0x00 }, len = 2
    // >> 60
    protected static int convertByte_To_int_LE(byte[] bytearray, int len) {
        ByteBuffer buffer = ByteBuffer.wrap(bytearray);
        buffer.order(ByteOrder.LITTLE_ENDIAN);

        if (len == 2) {
            return buffer.getShort() & 0xFFFF;
        } else if (len == 4) {
            return buffer.getInt();
        } else {
            return 0;
        }
    }

    protected static float convertByte_To_float(byte[] bytearray) {
        ByteBuffer buffer = ByteBuffer.wrap(bytearray);

        return buffer.getFloat();
    }

    protected static float convertByte_To_float_LE(byte[] bytearray) {
        ByteBuffer buffer = ByteBuffer.wrap(bytearray);
        buffer.order(ByteOrder.LITTLE_ENDIAN);

        return buffer.getFloat();
    }

    // byte[] test = { (byte) 0x41, (byte) 0x42, (byte) 0x43, (byte) 0x12, (byte) 0x34, (byte) 0x56, (byte) 0x78 (byte) 0x9A };
    // >> ABC123456789A
    protected static String hex_to_system_title(byte[] hexArray) {
        StringBuilder result = new StringBuilder();
        for (int i = 0; i < 3; i++) {
            result.append((char) hexArray[i]);
        }
        for (int i = 3; i < 8; i++) {
            String hex = String.format("%02X", hexArray[i] & 0xFF);
            result.append(hex.charAt(0));
            result.append(hex.charAt(1));
        }

        return result.toString();
    }

    // String test = "ABC123456789A";
    // >> { (byte) 0x41, (byte) 0x42, (byte) 0x43, (byte) 0x12, (byte) 0x34, (byte) 0x56, (byte) 0x78 (byte) 0x9A };
    protected static byte[] system_title_to_hex(String hexString) {
        String result = hexByte_To_HexString(hexString.substring(0, 3).getBytes(StandardCharsets.US_ASCII), 3) + hexString.substring(3, 13);

        return hexString_To_ByteArray(result);
    }
}
