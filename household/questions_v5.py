"""V5 categorical codes; order is meaningful except non-disclosure codes."""
INCOME = [
 ('lt_10000', 'Less than SEK 10,000'), ('10000_19999', 'SEK 10,000 to SEK 19,999'),
 ('20000_29999', 'SEK 20,000 to SEK 29,999'), ('30000_39999', 'SEK 30,000 to SEK 39,999'),
 ('40000_59999', 'SEK 40,000 to SEK 59,999'), ('60000_plus', 'SEK 60,000 or more'),
 ('dont_know', "Don't know"), ('prefer_not', 'Prefer not to tell')]
RENT = [('nothing', 'Nothing'), ('lt_5000', 'Less than SEK 5,000'),
 ('5000_9999', 'SEK 5,000 to SEK 9,999'), ('10000_14999', 'SEK 10,000 to SEK 14,999'),
 ('15000_19999', 'SEK 15,000 to SEK 19,999'), ('20000_plus', 'SEK 20,000 or more')]
CHILDREN = [('yes', 'Yes'), ('no', 'No'), ('prefer_not', 'Prefer not to say')]
EDUCATION = [('primary', 'Primary education'), ('lower_secondary', 'Lower secondary education'),
 ('upper_secondary', 'Upper secondary education'), ('bachelor', "Undergraduate degree (Bachelor's or equivalent)"),
 ('master', "Postgraduate degree (Master's or equivalent)"), ('doctorate', 'Doctoral degree (PhD) or higher'),
 ('prefer_not', 'Prefer not to tell')]
