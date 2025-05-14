import java.sql.*;

public class DB {
    // DB Driver
    static String DB_DRIVER = "com.mysql.jdbc.Driver";
    // DB IP:PORT/Database
    static String DB_URL = "jdbc:mysql://localhost:3306/";
    // DB ID
    static String DB_USER = "ID";
    // DB PW
    static String DB_PASSWORD = "PW";

    static {
        try {
            Class.forName(DB_DRIVER);
            System.out.println("[DB] Driver loaded");
        } catch (ClassNotFoundException e) {
            System.err.println("[DB] Driver load failed");
            e.printStackTrace();
        }
    }

    protected static Connection get_Connection() {
        try {
            return DriverManager.getConnection(DB_URL, DB_USER, DB_PASSWORD);
        } catch (SQLException e) {
            e.printStackTrace();
            return null;
        }
    }

    private static void use_Database(Statement stmt, String Database_Name) throws SQLException {
        stmt.executeUpdate("USE " + Database_Name);
        // System.out.println("[DB] Using Database : " + Database_Name);
    }

    protected static void check_Database(String Database_Name) {
        String check_Query = String.format("SHOW DATABASES LIKE '%s'", Database_Name);

        try (Connection DB_Conn = get_Connection();
                Statement stmt = DB_Conn.createStatement();
                ResultSet rs = stmt.executeQuery(check_Query)) {
            if (rs.next()) {
                // System.out.println("[DB] EXIST DATABASE : " + Database_Name);
            } else {
                // System.out.println("[DB] NOT EXIST DATABASE : " + Database_Name);
                System.out.println("[DB] CREATE DATABASE : " + Database_Name);
                stmt.executeUpdate("CREATE DATABASE " + Database_Name);
            }
        } catch (SQLException e) {
            System.err.println("[DB] Error Checking DATABASE [" + Database_Name + "].");
            e.printStackTrace();
        }
    }

    static protected void check_Table(String Database_Name, String Table_Name) {
        check_Database(Database_Name);

        String check_Query = String.format("SHOW TABLES LIKE '%s'", Table_Name);

        try (Connection DB_Conn = get_Connection();
                Statement stmt = DB_Conn.createStatement()) {
            use_Database(stmt, Database_Name);
            try (ResultSet rs = stmt.executeQuery(check_Query)) {
                if (rs.next()) {
                    System.out.println("[DB] Table [" + Table_Name + "] exists.");
                } else {
                    System.out.println("[DB] Table [" + Table_Name + "] not exist.");
                    create_Table(Table_Name);
                }
            }
        } catch (SQLException e) {
            System.out.println("[DB] Error Checking Table [" + Table_Name + "].");
            e.printStackTrace();
        }
    }

    protected static void check_And_Delete_Data(String Database_Name, String Table_Name, String Column_Name, String Value) {
        check_Table(Database_Name, Table_Name);

        String select_Query = String.format("SELECT * FROM %s WHERE %s = ?", Table_Name, Column_Name);
        String delete_Query = String.format("DELETE FROM %s WHERE %s = ?", Table_Name, Column_Name);

        try (Connection DB_Conn = get_Connection();
                Statement stmt = DB_Conn.createStatement()) {
            use_Database(stmt, Database_Name);
            try (PreparedStatement pstmt = DB_Conn.prepareStatement(select_Query)) {
                pstmt.setString(1, Value);
                try (ResultSet rs = pstmt.executeQuery()) {
                    if (rs.next()) {
                        System.out.println("[DB] Value found. Proceeding to delete.");
                        try (PreparedStatement dstmt = DB_Conn.prepareStatement(delete_Query)) {
                            dstmt.setString(1, Value);
                            int deleted = dstmt.executeUpdate();
                            System.out.println("[DB] Number of deleted rows : " + deleted);
                        }
                    } else {
                        System.out.println("[DB] Value does not exist.");
                    }
                }
            }
        } catch (SQLException e) {
            System.err.println("[DB] An error occurred during check_And_Delete_Data.");
            e.printStackTrace();
        }
    }

    protected static void check_And_Delete_Data_TwoColumns(String Database_Name, String Table_Name, String Column1_Name, String Value1, String Column2_Name, String Value2) {
        check_Table(Database_Name, Table_Name);

        String select_Query = String.format("SELECT * FROM %s WHERE %s = ? AND %s = ?", Table_Name, Column1_Name, Column2_Name);
        String delete_Query = String.format("DELETE FROM %s WHERE %s = ? AND %s = ?", Table_Name, Column1_Name, Column2_Name);

        try (Connection DB_Conn = get_Connection();
                Statement stmt = DB_Conn.createStatement()) {
            use_Database(stmt, Database_Name);
            try (PreparedStatement pstmt = DB_Conn.prepareStatement(select_Query)) {
                pstmt.setString(1, Value1);
                pstmt.setString(2, Value2);
                try (ResultSet rs = pstmt.executeQuery()) {
                    if (rs.next()) {
                        System.out.println("[DB] Matching values found. Proceeding to delete.");
                        try (PreparedStatement dstmt = DB_Conn.prepareStatement(delete_Query)) {
                            dstmt.setString(1, Value1);
                            dstmt.setString(2, Value2);
                            int deleted = dstmt.executeUpdate();
                            System.out.println("[DB] Number of deleted rows : " + deleted);
                        }
                    } else {
                        System.out.println("[DB] Matching values do not exist.");
                    }
                }
            }
        } catch (SQLException e) {
            System.out.println("[DB] An error occurred during check_And_Delete_Data_TwoColumns.");
            e.printStackTrace();
        }
    }

    static protected void create_Table(String Table_Name) {
        String createTableSQL = "";

        switch (Table_Name) {
            case "Test":
                createTableSQL = "CREATE TABLE Test( " +
                        "Server_Receive DATETIME DEFAULT CURRENT_TIMESTAMP);";
                break;

            default:
                System.out.println("[Error] Not Table");
                return;
        }

        try (Connection DB_Conn = get_Connection();
                Statement stmt = DB_Conn.createStatement();) {
            stmt.executeUpdate(createTableSQL);
            System.out.println("[DB] Table [" + Table_Name + "] created successfully.");
        } catch (SQLException e) {
            System.err.println("[DB] Error creating Table [" + Table_Name + "]");
            e.printStackTrace();
        }
    }
}
