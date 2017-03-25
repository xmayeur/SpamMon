import sqlite3

import pandas as pd
from fabric.api import *

env.host_string = 'rpiMON'
env.user = 'pi'
env.use_ssh_config = True

get('~/SpamMon/spam.db', '.')

con = sqlite3.connect('spam.db')
df = pd.read_sql('SELECT * FROM spam', con)
writer = pd.ExcelWriter('spam.xlsx', engine='xlsxwriter')
df.to_excel(writer, sheet_name='Sheet1')
writer.save()
writer.close()
