/*
 * Copyright 2008 University of Chicago/Argonne National Laboratory
 */

import java.util.Vector;

import java.sql.Connection;
import java.sql.Statement;
import java.sql.ResultSet;
import java.sql.PreparedStatement;
import java.sql.DriverManager;

/**
 * @author Neill Miller
 */
public class ESGOpenIDRetriever
{
    public class Options
    {
        public int verbose;
        public String host;
        public String user;
        public String pass;
        public String db;
        public String username;
        public String gateway;

        public Options() { }
    }

    private Options options = null;
    private Connection conn = null;

    public ESGOpenIDRetriever()
    {
        this.options = new Options();
    }

    public void setOptions(
        String dbHost, String dbUser, String dbPass, String dbName,
        String username, String gateway, int verbose)
    {
        this.options = new Options();
        this.options.host = dbHost;
        this.options.user = dbUser;
        this.options.pass = dbPass;
        this.options.db = dbName;
        this.options.username = username;
        this.options.gateway = gateway;
        this.options.verbose = verbose;
    }

    public String getOpenIDInformation() throws Exception
    {
        String openID = null;

        if ((this.options.host == null) || (this.options.user == null) ||
            (this.options.pass == null) || (this.options.db == null))
        {
            throw new Exception("Uninitialized database settings " +
                                "in getGroupInformation");
        }

        if (this.conn == null)
        {
            String url = "jdbc:postgresql://" + this.options.host + "/" + this.options.db;

            if (this.options.verbose != 0)
            {
                System.out.println("Attempting connection to " + url);
            }

            try
            {
                Class.forName("org.postgresql.Driver").newInstance();
                this.conn = DriverManager.getConnection(
                    url, this.options.user, this.options.pass);
            }
            catch(Exception e)
            {
                throw new Exception(
                    "Cannot connect to " + url + ": " + e);
            }
        }

        try
        {
            //esgcet=# SELECT DISTINCT openid FROM esgf_security.user
            //         WHERE username='gavinbell' AND openid LIKE 'https://esgf-node1.llnl.gov/esgf-idp/openid/%';
            //    openid
            //    -------------------------------------------------------
            //    https://esgf-node1.llnl.gov/esgf-idp/openid/gavinbell

            PreparedStatement openIdQuery = this.conn.prepareStatement(
                "select distinct openid from esgf_security.user " +
                "where username = ? AND openid like ?");

            openIdQuery.setString(1, this.options.username);
            openIdQuery.setString(2, this.options.gateway+"%");

            ResultSet rs = openIdQuery.executeQuery();

            while(rs.next())
            {
                openID = rs.getString("openid");
            }
        }
        catch(Exception e)
        {
            throw new Exception("Openid Query Failed: " + e);
        }
        return openID;
    }

    public static ESGOpenIDRetriever parseCmdLineArguments(String[] args)
    {
        ESGOpenIDRetriever openidRetr = new ESGOpenIDRetriever();

        for(int i = 0; i < args.length; i++)
        {
            if (args[i].equals("-h"))
            {
                openidRetr.options.host = args[i+1];
                i++;
                continue;
            }
            if (args[i].equals("-u"))
            {
                openidRetr.options.user = args[i+1];
                i++;
                continue;
            }
            if (args[i].equals("-p"))
            {
                openidRetr.options.pass = args[i+1];
                i++;
                continue;
            }
            if (args[i].equals("-d"))
            {
                openidRetr.options.db = args[i+1];
                i++;
                continue;
            }
            if (args[i].equals("-U"))
            {
                openidRetr.options.username = args[i+1];
                i++;
                continue;
            }
            if (args[i].equals("-g"))
            {
                openidRetr.options.gateway = args[i+1];
                i++;
                continue;
            }

            if (args[i].equals("-v"))
            {
                openidRetr.options.verbose = 1;
                continue;
            }
        }

        if ((openidRetr.options.host != null) && (openidRetr.options.host.length() > 0) &&
            (openidRetr.options.user != null) && (openidRetr.options.user.length() > 0) &&
            (openidRetr.options.pass != null) && (openidRetr.options.pass.length() > 0) &&
            (openidRetr.options.db != null) && (openidRetr.options.db.length() > 0))
        {
            if (openidRetr.options.verbose != 0)
            {
                System.out.println("Host    : " + openidRetr.options.host);
                System.out.println("DB User : " + openidRetr.options.user);
                System.out.println("Pass    : " + openidRetr.options.pass);
                System.out.println("DB      : " + openidRetr.options.db);
                System.out.println("Username: " + openidRetr.options.username);
                System.out.println("Gateway : " + openidRetr.options.gateway);
                System.out.println("Verbose : " + openidRetr.options.verbose);
            }
            return openidRetr;
        }
        return null;
    }

    public static void main(String[] args)
    {
        if (args.length > 9)
        {
            try
            {
                ESGOpenIDRetriever openidRetr = parseCmdLineArguments(args);
                String openid = openidRetr.getOpenIDInformation();
                System.out.println(openid);
            }
            catch(Exception e)
            {
                System.err.println("An error occurred: " + e);
            }
        }
        else
        {
            System.out.println(
                "\nUsage: java ESGOpenIDRetriever [-v] -h <DB Host:Port> -u <DB User> -p " +
                "<DB Password> -d <DBName> -g <openid dirname> -U <username>\n");
            System.out.println("*** All arguments are required except -v (for verbose)!\n");
            return;
        }
    }
}
