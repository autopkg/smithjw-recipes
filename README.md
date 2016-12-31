# smithjw-recipes
[smithjw's](https://twitter.com/smithjw) AutoPkg recipes

⚠️⚠️**Please be aware that pushing software directly into Self Service for all users without testing is a potentially risky action.**⚠️⚠️

With that warning out of the way, what are `-selfservice` recipies and what do they do? Well, it's fairly self explanitory, they are AutoPkg Recipes that build upon `jss` recipes to push new software versions into Self Service, bypassing the testing step that is required in `jss` recipes (`jss` recipes push the latest version of software into Self Service but restrict access to a Static Group of test machines that you define. 

This workflow comes directly from the work of [@homebysix](https://twitter.com/homebysix) in his [Auto-Update-Magic repo](https://github.com/homebysix/auto-update-magic). 

I would recommend reading [@homebysix's original exersice](https://github.com/homebysix/auto-update-magic#exercise-6c-sending-software-directly-to-self-service-policies) that documents the process of sending app updates directly to Self Service bypassing a group of test Macs. Actually, set aside a couple hours, grab yourself a 🍺/🍷, and read the [whole thing](https://github.com/homebysix/auto-update-magic#overview). A lot of thought and effort has gone into Auto-Update-Magic and I believe it makes life significantly easier for Mac Admins everywhere.

---

Need to add in Apache licence and reference to the template files from https://github.com/homebysix/auto-update-magic/ that I've made use of to implement Auto-updating Apps in Self Service
