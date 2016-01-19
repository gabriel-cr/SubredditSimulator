import HTMLParser
from datetime import datetime, timedelta
import pytz
import random
import re

from database import db
from models import Account, Settings, TopTodayAccount


class Simulator(object):
    def __init__(self):
        self.accounts = {account.name: account
            for account in db.query(Account)}
        self.subreddit = Settings["subreddit"]

        self.mod_account = self.accounts["subredditsim_ro_test"]

    def pick_account_to_comment(self):
        accounts = [a for a in self.accounts.values() if a.can_comment]

        # if any account hasn't commented yet, pick that one
        try:
            return next(a for a in accounts if not a.last_commented)
        except StopIteration:
            pass

        accounts = sorted(accounts, key=lambda a: a.last_commented)
        num_to_keep = len(accounts)
        return random.choice(accounts[:num_to_keep])

    def pick_account_to_submit(self):
        accounts = [a for a in self.accounts.values()  if (a.is_able_to_submit)]

        # if any account hasn't submitted yet, pick that one
        try:
            return next(a for a in accounts if not a.last_submitted)
        except StopIteration:
            pass

        accounts = sorted(accounts, key=lambda a: a.last_submitted)
        num_to_keep = len(accounts)
        
        result = random.choice(accounts[:num_to_keep])

        return result

    def retrieve_comments(self, name=""):
        account = self.accounts[name]
        account.retrieve_comments()

    def make_comment(self, name = ""):
        if name == "":
            account = self.pick_account_to_comment()
        else:
            account = self.accounts[name]
        
        if (account.special_class == "userbot"):
            account.train_from_comments(False)
        else:
            account.train_from_comments(True)
        # get the newest submission in the subreddit
        subreddit = account.session.get_subreddit(self.subreddit)
        for submission in subreddit.get_new(limit=5):
            if submission.author.name != Settings["owner"]:
                break
        account.post_comment_on(submission)

    def make_custom_submission(self, name=""):
        account = self.accounts[name]
        account.train_from_submissions()
        account.post_submission(self.subreddit)

    def make_submission(self):
        account = self.pick_account_to_submit()
        account.train_from_submissions()
        account.post_submission(self.subreddit)

    def update_leaderboard(self, limit=100):
        session = self.mod_account.session
        slist = self.mod_account.get_subreddits_list()
        
        stats = "\n\nStats:\n" 
        stats += "\nSubreddit | Comms | Subs\n"
        stats += "---|---|----\n"
        for s in slist:
            stats += "%s | %d | %d \n" % (
                str(s[0]).encode('utf-8'),
                self.mod_account.get_nb_comments_from_subreddit(s),
                self.mod_account.get_nb_subs_from_subreddit(s))
            

        subreddit = session.get_subreddit(self.subreddit)

        start_delim = "[](/leaderboard-start)"
        end_delim = "[](/leaderboard-end)"
        current_sidebar = subreddit.get_settings()["description"]
        current_sidebar = HTMLParser.HTMLParser().unescape(current_sidebar)
        replace_pattern = re.compile(
            "{}.*?{}".format(re.escape(start_delim), re.escape(end_delim)),
            re.IGNORECASE|re.DOTALL|re.UNICODE,
        )
        new_sidebar = re.sub(
            replace_pattern,
            "{}\n\n{}\n\n{}".format(start_delim, stats, end_delim),
            current_sidebar,
        )
        subreddit.update_settings(description=new_sidebar)

    def print_accounts_table(self):
        accounts = sorted(self.accounts.values(), key=lambda a: a.added)
        accounts = [a for a in accounts if not isinstance(a, TopTodayAccount)]
        
        print "Subreddit|Added|Posts Comments?|Posts Submissions?"
        print ":--|--:|:--|:--"

        checkmark = "&#10003;"
        for account in accounts:
            print "[{}]({})|{}|{}|{}".format(
                account.subreddit,
                "/u/" + account.name,
                account.added.strftime("%Y-%m-%d"),
                checkmark if account.can_comment else "",
                checkmark if account.can_submit else "",
            )
