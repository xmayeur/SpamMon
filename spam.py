from configobj import ConfigObj

INI_file = 'SpamMon.conf'
config = ConfigObj(INI_file)

if 'mysql' in config:
    from cryptography.fernet import Fernet
    import Key
    import pymysql
    import pymysql.cursors
    MYSQL = True
else:
    import sqlite3
    MYSQL = False


class Spam(object):


    def __init__(self):
        self.__status = ''

        # Connect to the database

        if MYSQL:
            try:
                key = Key.key
                f = Fernet(key)
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
                except pymysql.Error, e:
                    self.__status = "Error: Can't connect to the database - %s" % e

            except:
                self.__status = 'Error: Invalid or missing options in section [mysql] of config file'
        else:
            try:
                db = 'spam.db'
                self.connection = sqlite3.connect(db)
            except sqlite3.Error, e:
                self.__status = "Error: Can't connect to the database - %s" % e

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()

    def __enter__(self):
        return self

    def add(self, address):
        # Add a new record
        try:
            if MYSQL:
                with self.connection.cursor() as cursor:
                    sql = "INSERT INTO `spam` (`address`) VALUES (%s)"
                    cursor.execute(sql, (address,))
            else:
                cursor = self.connection.cursor()
                sql = "INSERT INTO `spam` (`address`) VALUES (?)"
                cursor.execute(sql, (address,))
            self.connection.commit()
            return True
        except:
            return False

    def remove(self, address):
        # delete a record
        try:
            if MYSQL:
                with self.connection.cursor() as cursor:
                    sql = "DELETE FROM `spam` WHERE `address` = %s"
                    cursor.execute(sql, (address,))
            else:
                cursor = self.connection.cursor()
                sql = "DELETE FROM `spam` WHERE `address` = ?"
                cursor.execute(sql, (address,))
            self.connection.commit()
            return True
        except:
            return False

    def exist(self, address):
        try:
            domain = '*@'+address.split('@')[1]
        except IndexError:
            domain = ''
            # print 'cannot get domain for %s' % address
        if MYSQL:
            with self.connection.cursor() as cursor:
                # check for blocked domain
                sql = "SELECT `address` FROM `spam` WHERE `address`=%s"
                cursor.execute(sql, (domain,))
                if cursor.fetchone() is not None:
                    return True
                # check else for blocked address
                sql = "SELECT `address` FROM `spam` WHERE `address`=%s"
                cursor.execute(sql, (address,))
                if cursor.fetchone() is not None:
                    return True
                else:
                    return False
        else:
            cursor = self.connection.cursor()
            # check for blocked domain
            sql = "SELECT `address` FROM `spam` WHERE `address`= ?"
            cursor.execute(sql, (domain,))
            if cursor.fetchone() is not None:
                return True
            # check else for blocked address
            sql = "SELECT `address` FROM `spam` WHERE `address`= ?"
            cursor.execute(sql, (address,))
            if cursor.fetchone() is not None:
                return True
            else:
                return False

    def close(self):
        self.connection.close()

    def configure(self):
        if MYSQL:
            with self.connection.cursor() as cursor:
                sql = '''CREATE TABLE IF NOT EXISTS `spam` (
                        `address` varchar(100) NOT NULL,
                        PRIMARY KEY  (`address`)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8
                '''
                cursor.execute(sql)
        else:
            cursor = self.connection.cursor()
            sql = '''CREATE TABLE IF NOT EXISTS `spam` (
                    `address` varchar(100) NOT NULL,
                    PRIMARY KEY  (`address`)
                    )
            '''
            cursor.execute(sql)

        self.connection.commit()

    @property
    def status(self):
        return self.__status

    @status.setter
    def status(self, value):
        raise Exception('Status is a read only property')

def main():
    with Spam() as s:
        s.configure()
        if s.status == '':
            if not s.add("www@ads.com"):
                print 'duplicate'
            if s.exist("www@ads.com"):
                print 'found'
                if s.remove("www@ads.com"):
                    print 'removed'



if __name__ == "__main__":
    main()