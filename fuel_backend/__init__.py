import pymysql

# ఇది Django ని మోసం చేయడానికి (వెర్షన్ ఎర్రర్ రాకుండా)
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()