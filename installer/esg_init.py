import esg_bash2py
'''
	Public

'''
#--------------
#User Defined / Settable (public)
#--------------
# _t=${0%.*}
 # expected=${2:-0}  -> expected=Bash2Py(Expand.colonMinus("2","0"))

install_prefix = esg_bash2py.Expand.colonMinus("install_prefix", esg_bash2py.Expand.colonMinus("ESGF_INSTALL_PREFIX", "/usr/local"))
esg_root_dir = esg_bash2py.Expand.colonMinus("esg_root_dir", esg_bash2py.Expand.colonMinus("ESGF_HOME", "/esg"))
esg_config_dir = esg_root_dir + "/config"
esg_config_type_file= esg_config_dir + "/config_type"
esgf_secret_file= esg_config_dir + "/.esgf_pass"
pg_secret_file= esg_config_dir + "/.esg_pg_pass"
pub_secret_file= esg_config_dir + "/.esg_pg_publisher_pass"
ks_secret_file= esg_config_dir + "/.esg_keystore_pass"
install_manifest = esg_bash2py.Expand.colonMinus("install_manifest", esg_root_dir+ "/esgf-install-manifest")
# logfile=${logfile:-"/tmp/${_t##*/}.out"}
# #--------------


def init():
    #--------------------------------
    # Internal esgf node code versions 
    #--------------------------------
	apache_frontend_version = esg_bash2py.Expand.colonMinus("apache_frontend_version", "v1.02")
	cdat_version = esg_bash2py.Expand.colonMinus("cdat_version", "2.2.0")
# #    cdat_tag="1.5.1.esgf-v1.7.0"

	esgcet_version = esg_bash2py.Expand.colonMinus("esgcet_version", "3.0.1")
	publisher_tag = esg_bash2py.Expand.colonMinus("publisher_tag", "v3.0.1")

#     #see esgf-node-manager project:
	esgf_node_manager_version = esg_bash2py.Expand.colonMinus("esgf_node_manager_version", "0.7.16")
	esgf_node_manager_db_version = esg_bash2py.Expand.colonMinus("esgf_node_manager_db_version", "0.1.5")

#     #see esgf-security project:
	esgf_security_version = esg_bash2py.Expand.colonMinus("esgf_security_version", "2.7.6")
	esgf_security_db_version = esg_bash2py.Expand.colonMinus("esgf_security_db_version", "0.1.5")

#     #see esg-orp project:
	esg_orp_version =esg_bash2py.Expand.colonMinus("esg_orp_version", "2.8.10")

#     #see esgf-idp project:
	esgf_idp_version = esg_bash2py.Expand.colonMinus("esgf_idp_version", "2.7.2")

#     #see esg-search project:
	esg_search_version = esg_bash2py.Expand.colonMinus("esg_search_version", "4.8.4")

#     #see esgf-web-fe project:
	esgf_web_fe_version = esg_bash2py.Expand.colonMinus("esgf_web_fe_version", "2.6.5")

#     #see esgf-dashboard project:
	esgf_dashboard_version = esg_bash2py.Expand.colonMinus("esgf_dashboard_version", "1.3.18")
	esgf_dashboard_db_version = esg_bash2py.Expand.colonMinus("esgf_dashboard_db_version", "0.01")

#     #see esgf-desktop project:
	esgf_desktop_version = esg_bash2py.Expand.colonMinus("esgf_desktop_version", "0.0.20")


init()