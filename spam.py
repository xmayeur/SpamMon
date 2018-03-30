from sqlalchemy import Column, String
from sqlalchemy import create_engine
from sqlalchemy import exc as sqlError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from SpamMon import get_vault, config, log

Base = declarative_base()


class SpamItem(Base):
    __tablename__ = 'spam'
    address = Column(String, primary_key=True)


def init_engine(dbms='mysql'):
    if dbms == 'mysql':
        uid = config.get('mysql', 'uid')
        host = config.get('mysql', 'host')
        db = config.get('mysql', 'db')
        u, p = get_vault(uid)
        s = 'mysql://' + u / ':' + p + '@' + host + '/' + db
    else:
        db = config.get('db', 'db')
        s = 'sqlite:///' + db
    
    return create_engine(s)


def create_table(e):
    Base.metadata.create_all(e)


def init_db_session(e):
    Base.metadata.bind = e
    DBsession = sessionmaker()
    DBsession.bind = e
    return DBsession()


class Spam(object):

    def __init__(self):
        # Connect to the database
        try:
            self.engine = init_engine()
            self.sql = init_db_session(self.engine)
            self.__status = ''
            log.info('Connected to Spam DB')
        except sqlError.SQLAlchemyError:
            log.error('Cannot initiate connection to database')

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sql.close()

    def __enter__(self):
        return self

    def add(self, address):
        # Add a new record
        try:
            self.sql.add(SpamItem(address=address))
            self.sql.commit()
            return True
        except sqlError.SQLAlchemyError:
            log.error('Cannot add an item into the database')
            return False

    def remove(self, address):
        # delete a record
        try:
            row = self.sql.query(SpamItem).filter(SpamItem.address == address).first()
            if row is not None:
                self.sql.delete(row)
                self.sql.commit()
                return True
            else:
                log.error('Item %s not found' % address)
                return False
        except sqlError.SQLAlchemyError:
            log.error('Cannot delete an item from the database')
            return False

    def exist(self, address):
        try:
            domain = '*@'+address.split('@')[1]
            row = self.sql.query(SpamItem).filter(SpamItem.address == domain).first()
            if row is not None:
                return True
        except IndexError:
            pass

        try:
            row = self.sql.query(SpamItem).filter(SpamItem.address == address).first()
            if row is not None:
                return True
            else:
                return False
        except sqlError.SQLAlchemyError:
            return False

    def close(self):
        self.sql.close()

    def configure(self):
        create_table(self.engine)

    @property
    def status(self):
        return self.__status

    @status.setter
    def status(self, value):
        raise Exception('Status is a read only property')


def main():
    pass


if __name__ == "__main__":
    main()
