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
public class ESGGroupRetriever
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

    public ESGGroupRetriever()
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

    public String getGroupAndRoleInformation() throws Exception
    {
        String infoStr = null;
        Vector<String> infoStrList = new Vector<String>();

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
            //esgcet=# select g.name, r.name from esgf_security.group as g, esgf_security.role as r, esgf_security.permission as p, esgf_security.user as u
            //    WHERE p.user_id = u.id and u.username = 'gavinbell' and u.openid like 'https://esgf-node1.llnl.gov/esgf-idp/openid/%'
            //    and p.group_id = g.id and p.role_id = r.id
            //    ORDER BY g.name;
            //         group     | role
            //    ----------------+------
            //    CMIP5 Research | User
            //    NASA OBS       | User
            //    ORNL OBS       | User

            PreparedStatement attrQuery = this.conn.prepareStatement(
                "select g.name as group, r.name as role "+
                "from esgf_security.group as g, esgf_security.role as r, esgf_security.permission as p, esgf_security.user as u "+
                "WHERE p.user_id = u.id and u.username = ? and u.openid like ? and p.group_id = g.id and p.role_id = r.id "+
                "ORDER BY g.name" );

            attrQuery.setString(1, this.options.username);
            attrQuery.setString(2, this.options.gateway+"%");

            ResultSet rs = attrQuery.executeQuery();

            while(rs.next())
            {
                if (infoStr == null)
                {
                    infoStr = "esg.vo.group.roles=" + "group_"+rs.getString("group")+"_role_"+rs.getString("role");
                }
                else
                {
                    infoStr += (";" + "group_"+rs.getString("group")+"_role_"+rs.getString("role"));
                }

                if (this.options.verbose != 0)
                {
                    System.out.println("Got Attribute: " + "group_"+rs.getString("group")+"_role_"+rs.getString("role"));
                }
            }
        }
        catch(Exception e)
        {
            //e.printStackTrace();
            throw new Exception("Group Query Failed: " + e);
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

            /* get the first openid that matches the username */
            ResultSet rs = openIdQuery.executeQuery();

            while(rs.next())
            {
                infoStr += (":esg.vo.openid=" + rs.getString("openid"));

                if (this.options.verbose != 0)
                {
                    System.out.println("Got OpenID: " + rs.getString("openid"));
                }
            }
        }
        catch(Exception e)
        {
            //e.printStackTrace();
            throw new Exception("Openid Query Failed: " + e);
        }
        return infoStr;
    }

    public static ESGGroupRetriever parseCmdLineArguments(String[] args)
    {
        ESGGroupRetriever esgGroupRetr = new ESGGroupRetriever();

        for(int i = 0; i < args.length; i++)
        {
            if (args[i].equals("-h"))
            {
                esgGroupRetr.options.host = args[i+1];
                i++;
                continue;
            }
            if (args[i].equals("-u"))
            {
                esgGroupRetr.options.user = args[i+1];
                i++;
                continue;
            }
            if (args[i].equals("-p"))
            {
                esgGroupRetr.options.pass = args[i+1];
                i++;
                continue;
            }
            if (args[i].equals("-d"))
            {
                esgGroupRetr.options.db = args[i+1];
                i++;
                continue;
            }
            if (args[i].equals("-U"))
            {
                esgGroupRetr.options.username = args[i+1];
                i++;
                continue;
            }
            if (args[i].equals("-g"))
            {
                esgGroupRetr.options.gateway = args[i+1];
                i++;
                continue;
            }

            if (args[i].equals("-v"))
            {
                esgGroupRetr.options.verbose = 1;
                continue;
            }
        }

        if ((esgGroupRetr.options.host != null) && (esgGroupRetr.options.host.length() > 0) &&
            (esgGroupRetr.options.user != null) && (esgGroupRetr.options.user.length() > 0) &&
            (esgGroupRetr.options.pass != null) && (esgGroupRetr.options.pass.length() > 0) &&
            (esgGroupRetr.options.db != null) && (esgGroupRetr.options.db.length() > 0))
        {
            if (esgGroupRetr.options.verbose != 0)
            {
                System.out.println("Host    : " + esgGroupRetr.options.host);
                System.out.println("DB User : " + esgGroupRetr.options.user);
                System.out.println("Pass    : " + esgGroupRetr.options.pass);
                System.out.println("DB      : " + esgGroupRetr.options.db);
                System.out.println("Username: " + esgGroupRetr.options.username);
                System.out.println("Gateway : " + esgGroupRetr.options.gateway);
                System.out.println("Verbose : " + esgGroupRetr.options.verbose);
            }
            return esgGroupRetr;
        }
        return null;
    }

    public static void main(String[] args)
    {
        if (args.length > 9)
        {
            try
            {
                ESGGroupRetriever esgGroupRetr = parseCmdLineArguments(args);
                String groupStr = esgGroupRetr.getGroupAndRoleInformation();
                System.out.println(groupStr);
            }
            catch(Exception e)
            {
                System.err.println("An error occurred: " + e);
            }
        }
        else
        {
            System.out.println(
                "\nUsage: java ESGGroupRetriever [-v] -h <DB Host:Port> -u <DB User> -p " +
                "<DB Password> -d <DBName> -g <openid dirname> -U <username>\n");
            System.out.println("*** All arguments are required except -v (for verbose)!\n");
            return;
        }
    }
}
