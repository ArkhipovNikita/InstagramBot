class Database:
    def __init__(self, cursor, conn, username):
        self.cursor = cursor
        self.conn = conn
        initial_user_id = self.add_inital_user(username)
        self.curr_user_id = initial_user_id
        self.passed_users_count = 0

    def execute(self, command):
        """
        Wrapper for usual command cursor.execute
        to commit changes straight off executing
        """
        try:
            self.cursor.execute(command)
            self.conn.commit()
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            print(message)

    def add_inital_user(self, username):
        command = f"INSERT INTO instagram_users (id, username) VALUES (nextval('instagram_user'), '{username}') RETURNING id;"
        self.execute(command)
        return self.cursor.fetchone()[0]

    def add_tagging_users(self, tagging_users: set):
        """
        Write all new usernames of visited users.
        Write all relationships: who tagged whom.
        When repeated do nothing.
        :param tagging_users: usernames of users that tagged current user
        """
        # inserting new users into instagram_users
        command = 'INSERT INTO instagram_users (id, username) VALUES '
        values = ["(nextval('instagram_user'), '%s')" % user for user in tagging_users]
        command += ', '.join(values) + ' ON CONFLICT (username) DO NOTHING RETURNING id;'
        self.execute(command)

        # inserting new relationships into instagram_users_links
        # get assigned ids in database sequence
        tagging_user_ids = [record[0] for record in self.cursor.fetchall()]
        command = 'INSERT INTO instagram_users_links (id, from_, to_) VALUES '
        values = ["(nextval('instagram_user'), '%s', '%s')" % (tagging_user_id, self.curr_user_id)
                  for tagging_user_id in tagging_user_ids]
        command += ', '.join(values) + 'ON CONFLICT (from_, to_) DO NOTHING;'
        self.execute(command)

    def get_next_user(self):
        """
        Return username that was added after current one
        """
        # Increase quantity of vidited users
        self.passed_users_count += 1
        self.execute("SELECT * FROM instagram_users LIMIT 1 OFFSET %s;" % self.passed_users_count)
        result = self.cursor.fetchone()
        if result is None:
            return ''
        # Assign new user's id
        self.curr_user_id = result[0]
        return result[1]

    def close(self):
        """
        Close all connections
        """
        self.cursor.close()
        self.conn.close()
