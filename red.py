import praw
import praw.errors
import nsfw

def main(userchoice):
    dic = []
    r = praw.Reddit(user_agent='Newsfetcher by /u/vicerunt')
    # Stores the entered subreddit in userchoice.
    # Gets 30 top posts from the specific subreddit.
    submissions = r.get_subreddit(userchoice.split('/')[-1]).get_top(limit=5)
    # Formats the printed output and adds a nice counter.
    if userchoice.split('/')[-1].lower() in nsfw.PURITAN_VALUES:
        pass
    else:
        submission_form = "{}) {} : {} <{}>"
        count = 1
        try:
            for sub in submissions:
                if sub not in dic:
                    subs = (submission_form.format(count, sub.ups, sub.title, sub.url))
                    dic.append(subs)
                count += 1
            return dic

        except praw.errors.NotFound:
            return []
