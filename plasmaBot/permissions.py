import os
import sys
import asyncio
import discord
import traceback

from . import exceptions

from plasmaBot.defaults.database_tables import dbt_glob_perms, dbt_server_perms

from SQLiteHelper import SQLiteHelper as sq

class Permissions:
    def __init__(self, perm_db_path, plasmaBot):
        self.perm_db = sq.Connect(perm_db_path)

        if not self.perm_db.table('global').tableExists():
            initiation_glob = dbt_glob_perms()
            self.perm_db.table('global').init(initiation_glob)
        if not self.perm_db.table('servers').tableExists():
            initiation_serv = dbt_server_perms()
            self.perm_db.table('servers').init(initiation_serv)

        self.bot = plasmaBot

    def set_server_permissions(self, server, admin_role_id, mod_role_id, helper_role_id, black_role_id):
        owner_id = ''
        current_server_return = self.perm_db.table('servers').select("OWNER_ID").where("SERVER_ID").equals(server.id).execute()
        for row in current_server_return:
            owner_id = row[0]
        if owner_id == '':
            if self.bot.config.debug:
                print('[PB][PERMISSIONS] Setting Permissions Data for Server {} [{}]'.format(server.name, server.id))
            self.perm_db.table('servers').insert(server.id, server.owner.id, admin_role_id, mod_role_id, helper_role_id, black_role_id).into("SERVER_ID", "OWNER_ID", "ADMINISTRATOR_ROLE_ID", "MODERATOR_ROLE_ID", "HELPER_ROLE_ID", "BLACKLISTED_ROLE_ID")
        else:
            if self.bot.config.debug:
                print('[PB][PERMISSIONS] Updating Permissions Data for Server {} [{}]'.format(server.name, server.id))
            self.perm_db.table('servers').update("OWNER_ID").setTo(server.owner.id).where("SERVER_ID").equals(server.id).execute()
            self.perm_db.table('servers').update("ADMINISTRATOR_ROLE_ID").setTo(admin_role_id).where("SERVER_ID").equals(server.id).execute()
            self.perm_db.table('servers').update("MODERATOR_ROLE_ID").setTo(mod_role_id).where("SERVER_ID").equals(server.id).execute()
            self.perm_db.table('servers').update("HELPER_ROLE_ID").setTo(helper_role_id).where("SERVER_ID").equals(server.id).execute()
            self.perm_db.table('servers').update("BLACKLISTED_ROLE_ID").setTo(black_role_id).where("SERVER_ID").equals(server.id).execute()

    async def check_permissions(self, user, channel, server=None):
        # 0 = Blacklisted
        # 5 = Standard User / No Server Features Enabled
        # 9 = Server User on Server without configured permissions
        # 10 = Standard User
        # 25 = Server's Helper Role
        # 30 = This Instance of the Bot
        # 35 = Server's Moderator Role
        # 45 = Server's Administrator Role
        # 50 = Server Owner & Adminstrator Permission Holders
        # 100 = Bot Owner
        permission_level = 0

        user_glob_permissions_return = self.perm_db.table('global').select('PERMISSIONS_LEVEL').where("USER_ID").equals(user.id).execute()

        if user.id == self.bot.user.id:
            permission_level = 30
            return permission_level

        for row in user_glob_permissions_return:
            permission_level = min(int(row[0]), 100)
            return permission_level

        if user.id == self.bot.config.owner_id or user.id == self.bot.config.debug_id:
            permission_level = 100
            return permission_level

        if server:
            server_permissions_return = self.perm_db.table('servers').select("OWNER_ID", "ADMINISTRATOR_ROLE_ID", "MODERATOR_ROLE_ID", "HELPER_ROLE_ID", "BLACKLISTED_ROLE_ID").where("SERVER_ID").equals(server.id).execute()

            s_owner = ''
            s_admin = ''
            s_moderator = ''
            s_helper = ''
            s_blacklist = ''

            for row in server_permissions_return:
                s_owner = row[0]
                s_admin = row[1]
                s_moderator = row[2]
                s_helper = row[3]
                s_blacklist = row[4]

            if channel.permissions_for(user).administrator:
                permission_level = 50
                return permission_level

            if s_owner == '':
                permission_level = 9
                return permission_level

            if user.id == s_owner:
                permission_level = 50
                return permission_level

            permission_level = 10

            for role in user.roles:
                if role.id == s_admin:
                    if 45 > permission_level:
                        permission_level = 45
                if role.id == s_moderator:
                    if 35 > permission_level:
                        permission_level = 35
                if role.id == s_helper:
                    if 25 > permission_level:
                        permission_level = 25
                if role.id == s_blacklist:
                    permission_level = 0
                    return permission_level

            return permission_level

        else:
            permission_level = 5
            return permission_level
