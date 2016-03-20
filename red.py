import praw
import praw.errors


def main(userchoice):
    dic = []
    r = praw.Reddit(user_agent='Newsfetcher by /u/vicerunt')
    # Stores the entered subreddit in userchoice.
    # Gets 30 top posts from the specific subreddit.
    submissions = r.get_subreddit(userchoice).get_top(limit=30)
    # Formats the printed output and adds a nice counter.
    submission_form = "{}) {} : {} <{}>"
    count = 1
    print("Top 30 Posts from", userchoice)
    print('-' * 25)
    try:
        for sub in submissions:
            if sub not in dic:
                subs = (submission_form.format(count, sub.ups, sub.title, sub.url))
                dic.append(subs)
            count += 1
        return dic

    except praw.errors.NotFound:
        print("Invalid subreddit!")
