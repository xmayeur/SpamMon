import Key
import pymysql
import pymysql.cursors
from configobj import ConfigObj
from cryptography.fernet import Fernet


class Spam:

    def __init__(self):
        # Connect to the database
        key = Key.key
        f = Fernet(key)
        INI_file = 'SpamMon.conf'
        try:
            config = ConfigObj(INI_file)
            host = config['mysql']['host']
            user = config['mysql']['user']
            password = config['mysql']['password']
            db = config['mysql']['db']

            try:
                self.connection = pymysql.connect(host=host,
                                                  user=user,
                                                  password=f.decrypt(password),
                                                  db=db,
                                                  charset='utf8mb4',
                                                  cursorclass=pymysql.cursors.DictCursor)
            except:
                print "Can't connect to the database"

        except:
            print 'Error: Invalid or missing options in section [mysql] of config file'



    def add(self, address):
        # Add a new record
        try:
            with self.connection.cursor() as cursor:
                sql = "INSERT INTO `spam` (`address`) VALUES (%s)"
                cursor.execute(sql, (address,))
            self.connection.commit()
            return True
        except:
            return False

    def remove(self, address):
        # delete a record
        try:
            with self.connection.cursor() as cursor:
                sql = "DELETE FROM `spam` WHERE `address` = %s"
                cursor.execute(sql, (address,))
            self.connection.commit()
            return True
        except:
            return False

    def exist(self, address):
        try:
            domain = '*@'+address.split('@')[1]
        except IndexError:
            domain=''
            # print 'cannot get domain for %s' % address
        with self.connection.cursor() as cursor:
            # check for blocked domain
            sql = "SELECT `address` FROM `spam` WHERE `address`=%s"
            cursor.execute(sql, (domain,))
            if cursor.fetchone() != None :
                return True
            # check else for blocked address
            sql = "SELECT `address` FROM `spam` WHERE `address`=%s"
            cursor.execute(sql, (address,))
            if cursor.fetchone() != None :
                return True
            else:
                return False

    def close_db(self):
        self.connection.close()

    def configure(self):
        with self.connection.cursor() as cursor:
            sql = '''CREATE TABLE IF NOT EXISTS `spam` (
                    `address` varchar(100) NOT NULL,
                    PRIMARY KEY  (`address`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8
            '''
            cursor.execute(sql)
        self.connection.commit()

def main():
    s = Spam()
    if s.add("www@ads.com") == False:
        print 'duplicate'
    if s.exist("www@ads.com"):
        print 'found'
        if s.remove("www@ads.com"):
            print 'removed'

if __name__ == "__main__":
    main()