# title_categorizer.py

def categorize_title(title):
    # Ensure that the title is a string
    if not isinstance(title, str):
        return title  # or return 'Unknown' if you want to label non-strings explicitly

    title_lower = title.lower()
    if 'chief executive officer' in title_lower:
        return 'CEO'
    elif 'chief financial officer' in title_lower:
        return 'CFO'
    elif 'vice president' in title_lower:
        return 'Vice President'
    elif 'manager' in title_lower:
        return 'Manager'
    elif 'president' in title_lower and 'vice president' not in title_lower:
        return 'President'
    elif 'member' in title_lower:
        return 'Member'
    # This will match any title with 'owner' in it, including 'Owner/Principal'
    elif 'owner' in title_lower:
        return 'Owner'
    # This will only match titles that have 'principal' without 'owner'
    elif 'principal' in title_lower:
        return 'Principal'
    elif 'treasurer' in title_lower:
        return 'Treasurer'
    elif 'senior' in title_lower:
        return 'Senior Executive'
    elif 'director' in title_lower:
        return 'Director'
    elif 'administrator' in title_lower:
        return 'Administrator'
    elif 'secretary' in title_lower:
        return 'Secretary'
    elif 'illustrator' in title_lower:
        return 'Illustrator'
    elif 'professor' in title_lower:
        return 'Professor'
    elif 'surgeon' in title_lower:
        return 'Surgeon'
    else:
        return title
