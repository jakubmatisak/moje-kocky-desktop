; Texty inštalátora a odinštalovania po slovensky a po anglicky.
; Jazyk vyberie Inno Setup podľa jazyka Windows (alebo voľby na začiatku
; inštalácie) a odinštalovanie ide v jazyku inštalácie. Skripty berú texty
; cez CustomMessage('Meno') a {cm:Meno}; %1 a %2 dopĺňa FmtMessage, %n je
; nový riadok. Každá hláška musí byť v oboch jazykoch (tests/test_installer.py).
; Súbor vkladá moje-kocky.iss za [Languages] a testovací inštalátor v teste.

[CustomMessages]
; Položka v ponuke Štart (THIRD-PARTY-NOTICES.txt).
slovak.ThirdPartyNotices=Licencie softvéru tretích strán
english.ThirdPartyNotices=Third-party software licences

; Chýbajúci WebView2 (InitializeSetup v moje-kocky.iss).
slovak.WebView2Missing=Moje kocky potrebujú súčasť Microsoft Edge WebView2, ktorá na tomto počítači chýba.%nOtvoriť stránku Microsoftu na jej stiahnutie?
english.WebView2Missing=Moje kocky needs the Microsoft Edge WebView2 component, which is missing on this computer.%nOpen the Microsoft page to download it?

; Odinštalovanie (uninstall-data.iss): %1 účet Windows, %2 priečinok údajov.
slovak.DeleteDataQuestion=Zmazať aj údaje Moje kocky (zbierku, fotky, kľúče) používateľa Windows „%1“ v priečinku %2?%nÚdaje ostatných používateľov počítača ostanú. Ak ich necháš, nová inštalácia ich znova použije.
english.DeleteDataQuestion=Also delete the Moje kocky data (collection, photos, keys) of Windows user "%1" in the folder %2?%nThe data of other users of this computer stays. If you keep it, a new install will use it again.
; %1 účet správcu, pod ktorým odinštalovanie bežalo, %2 používateľ pri počítači.
slovak.OtherAccountNotice=Odinštalovanie bežalo pod účtom správcu „%1“, nie pod tvojím („%2“), preto údaje Moje kocky nemazalo nikomu.%nTvoje údaje (zbierka, fotky, kľúče) ostali v priečinku %APPDATA%\MojeKocky tvojho účtu. Keď ich už nechceš, zmaž ho sám; ak ho necháš, nová inštalácia ich znova použije.
english.OtherAccountNotice=Uninstall ran under the administrator account "%1", not under yours ("%2"), so it deleted no one's Moje kocky data.%nYour data (collection, photos, keys) stayed in the %APPDATA%\MojeKocky folder of your account. If you no longer want it, delete that folder yourself; if you keep it, a new install will use it again.

; Stará inštalácia 0.1.x (old-install.iss): %1 priečinok starého programu.
slovak.OldInstallUnknownFolder=Staršia verzia Moje kocky je v priečinku %1, ktorý inštalátor sám nezmaže.%nOdinštaluj ju v Nastaveniach → Aplikácie (otázku, či zmazať aj údaje, zamietni; zbierka ostane) a spusti inštaláciu znova.
english.OldInstallUnknownFolder=An older version of Moje kocky is in the folder %1, which the installer does not delete by itself.%nUninstall it in Settings → Apps (decline the question whether to delete the data too; the collection stays) and run the installer again.
slovak.OldInstallLeftovers=Priečinok staršej verzie %1 sa nepodarilo celý zmazať, niečo v ňom ešte používa iný program.%nZavri programy, ktoré ho môžu používať (aj okno Prieskumníka alebo príkazového riadka v ňom), a spusti inštaláciu znova.
english.OldInstallLeftovers=The folder of the older version %1 could not be deleted completely, another program is still using something in it.%nClose the programs that may be using it (also a File Explorer or command prompt window in it) and run the installer again.
slovak.OldInstallRunning=Zavri Moje kocky a spusti inštaláciu znova.%nStaršia verzia z priečinka %1 je ešte otvorená.
english.OldInstallRunning=Close Moje kocky and run the installer again.%nThe older version from the folder %1 is still open.
