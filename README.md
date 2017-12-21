AST (sorta) + Random Forest to predict buggy functions.
Only implemented for php, but adding parser to /buggin/syntax_parser/ for different languages does the trick.

TO DO
-----
- actually spit out the names of buggy functions
- general code cleanup
- lots o docing
- refactor to enable tool to be used as library
- add some other languages (probs start with java)
- make is_bug_commit function configurable
- get scientific about which measures are used... initially just added all of them and commented out when i saw fit
- make tool easier to run
- setup.sh
