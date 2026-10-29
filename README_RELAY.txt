NEON ROYALE RELAY SERVER - FREE DEPLOY (Render.com)
===================================================
Yeh server doston ko alag-alag network se jodta hai. Sab kuch free hai (card nahi chahiye).

STEP 1 - GitHub par files daalo
 1. github.com par free account banao (ya login karo).
 2. Upar "+" > "New repository". Naam: neon-relay. "Public" rakho. "Create repository".
 3. "uploading an existing file" link dabao, is folder ki 2 files (server.py aur requirements.txt) drag-drop karo.
 4. "Commit changes" dabao.

STEP 2 - Render par chalao
 1. render.com par jao > "Get Started" > "GitHub" se login karo.
 2. "New +" > "Web Service" > apni neon-relay repo chuno > "Connect".
 3. Settings:
      Name: neon-relay (kuch bhi)
      Region: Singapore   (India ke liye sabse tez)
      Runtime/Language: Python 3
      Build Command: pip install -r requirements.txt
      Start Command: python server.py
      Instance Type: Free
 4. "Create Web Service" dabao. 2-3 minute ruko jab tak "Live" na dikhe.
 5. Upar ek link dikhega, jaise https://neon-relay-abcd.onrender.com
    Use browser me kholo. "Neon Royale relay OK" likha aaye to server sahi hai.

STEP 3 - Game me use karo
 1. Lobby me CREATE ROOM ya JOIN ROOM chuno.
 2. "Internet se khelo (Room code)" tick karo.
 3. Relay link wale box me woh https://....onrender.com link paste karo (ek baar; game yaad rakhta hai).
 4. Host: CREATE ROOM dabao -> 5 akshar ka Room code dikhega (jaise AB7K2). Doston ko bhejo.
 5. Dost: JOIN ROOM, wahi code likho, JOIN ROOM dabao.

IMPORTANT BAATEIN
 - Free Render server 15 minute koi use na ho to so jata hai. Pehli baar connect hone me ~1 minute lag sakta hai
   (game khud retry karta hai, "connect ho raha hoon" dikhega).
 - Har dost ko link box me link paste karna padega. Ya ek baar main.gd me RELAY_DEFAULT = "https://....onrender.com" likhke
   game export karo, phir kisi ko kuch likhna nahi padega.
 - Server sirf packets aage bhejta hai. Free plan me bahut saare players ke liye nahi, doston ke liye theek hai.
