import pymysql.cursors
import pymysql


class Spam:

    def __init__(self):
        # Connect to the database
        host = 'nas'
        user = 'admin'
        password = 'Bretzel58'
        db = 'mayeur_be'
        self.connection = pymysql.connect(host=host,
                                     user=user,
                                     password=password,
                                     db=db,
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)

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


def main():
    s = Spam()
    if s.add("www.ads.com") == False:
        print 'duplicate'
    if s.exist("www.ads.com"):
        print 'found'
        if s.remove("www.ads.com"):
            print 'removed'

if __name__ == "__main__":
    main()