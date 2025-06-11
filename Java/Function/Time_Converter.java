import java.time.DayOfWeek;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class Time_Converter {
    protected static byte HEXtoBCD(int val) {
        return (byte) ((((val / 10) << 4) & 0xF0) | (val % 10 & 0x0F));
    }

    protected static int BCDtoHEX(byte val) {
        return (((val >> 4) & 0x0F) * 10) + (val & 0x0F);
    }

    protected static String localTime_To_MysqlTime() {
        LocalDateTime now = LocalDateTime.now();
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
        return now.format(formatter);
    }

    protected static byte[] dateString_To_ByteArray(String dateString) {
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
        LocalDateTime dateTime = LocalDateTime.parse(dateString, formatter);

        byte year = HEXtoBCD(dateTime.getYear() % 100);
        byte month = HEXtoBCD(dateTime.getMonthValue());
        byte day = HEXtoBCD(dateTime.getDayOfMonth());
        byte week = getWeekByte(dateTime.getDayOfWeek());
        byte hour = HEXtoBCD(dateTime.getHour());
        byte minute = HEXtoBCD(dateTime.getMinute());
        byte second = HEXtoBCD(dateTime.getSecond());

        return new byte[]{year, month, day, week, hour, minute, second};
    }

    private static byte getWeekByte(DayOfWeek dayOfWeek) {
        int dayValue = dayOfWeek.getValue();
        return (byte) (dayValue % 7); // Sunday = 0, Monday = 1 ...
    }

    protected static String packetTime_To_MysqlTime(byte[] time) {
        int year = BCDtoHEX(time[0]) + 2000;
        int month = Math.max(BCDtoHEX(time[1]), 1);
        int day = Math.max(BCDtoHEX(time[2]), 1);
        int hour = BCDtoHEX(time[4]);
        int minute = BCDtoHEX(time[5]);
        int second = BCDtoHEX(time[6]);

        return String.format("%04d-%02d-%02d %02d:%02d:%02d", year, month, day, hour, minute, second);
    }

    protected static String packetDLMSTime_To_MysqlTime(byte[] dlmstime) {
        byte[] forward_time = new byte[8];

        int raw_year = (((dlmstime[0] & 0xFF) << 8) | (dlmstime[1] & 0xFF));
        int year_mod_100 = raw_year % 100;
        forward_time[0] = HEXtoBCD(year_mod_100);
        forward_time[1] = HEXtoBCD(dlmstime[2] & 0xFF);
        forward_time[2] = HEXtoBCD(dlmstime[3] & 0xFF);
        forward_time[3] = HEXtoBCD(dlmstime[4] & 0xFF);
        forward_time[4] = HEXtoBCD(dlmstime[5] & 0xFF);
        forward_time[5] = HEXtoBCD(dlmstime[6] & 0xFF);
        forward_time[6] = HEXtoBCD(dlmstime[7] & 0xFF);

        int year = BCDtoHEX(forward_time[0]) + 2000;
        int month = BCDtoHEX(forward_time[1]);
        int day = BCDtoHEX(forward_time[2]);
        int hour = BCDtoHEX(forward_time[4]);
        int minute = BCDtoHEX(forward_time[5]);
        int second = BCDtoHEX(forward_time[6]);

        return String.format("%04d-%02d-%02d %02d:%02d:%02d", year, month, day, hour, minute, second);
    }

    protected static byte[] time_To_packetDLMSTime(String time) {
        byte[] dlms = new byte[12];
        try {
            DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
            LocalDateTime forward_time = LocalDateTime.parse(time, formatter);

            int year = forward_time.getYear();
            int month = forward_time.getMonthValue();
            int day = forward_time.getDayOfMonth();
            int dayOfWeek = forward_time.getDayOfWeek().getValue();
            int hour = forward_time.getHour();
            int minute = forward_time.getMinute();
            int second = forward_time.getSecond();

            dlms[0] = (byte) ((year >> 8) & 0xFF);
            dlms[1] = (byte) (year & 0xFF);
            dlms[2] = (byte) month;
            dlms[3] = (byte) day;
            dlms[4] = (byte) dayOfWeek;
            dlms[5] = (byte) hour;
            dlms[6] = (byte) minute;
            dlms[7] = (byte) second;

            dlms[8] = (byte) 0xFF; // Hundredths of second (not used)
            dlms[9] = (byte) 0xFF; // Deviation (UTC offset - not used)
            dlms[10] = (byte) 0x00; // Clock status
            dlms[11] = (byte) 0x00; // Reserved or extension

        } catch (Exception e) {
            e.printStackTrace();
        }
        return dlms;
    }

    protected static void DLMSTime_To_Time(byte[] dlmstime, byte[] time) {
        byte[] forward_time = new byte[8];
        int raw_year = ((dlmstime[0] & 0xFF) << 8) | (dlmstime[1] & 0xFF);
        forward_time[0] = HEXtoBCD(raw_year % 100);
        forward_time[1] = HEXtoBCD(dlmstime[2] & 0xFF);
        forward_time[2] = HEXtoBCD(dlmstime[3] & 0xFF);
        forward_time[3] = HEXtoBCD(dlmstime[4] & 0xFF);
        forward_time[4] = HEXtoBCD(dlmstime[5] & 0xFF);
        forward_time[5] = HEXtoBCD(dlmstime[6] & 0xFF);
        forward_time[6] = HEXtoBCD(dlmstime[7] & 0xFF);

        System.arraycopy(forward_time, 0, time, 0, 7);
    }
}
