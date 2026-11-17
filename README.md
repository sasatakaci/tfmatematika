# TF Matematika — probna verzija

Nezavisna Streamlit aplikacija za evidenciju predmeta, studenata, K1, K2, završnog ispita, ponovljenih kolokvijuma i položenih ispita.

## Pokretanje

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Pravila

- Predmet je određen nazivom i školskom godinom (početni primer: Matematika 1, 2025/26).
- K1 30, K2 30, završni ispit 30, aktivnost 10.
- Za prolaz: K1+K2 najmanje 30, završni najmanje 16, ukupan zbir najmanje 51. Ocene 6/7/8/9/10 počinju od 51/61/71/81/91.
- Za svaki tip provere koristi se najbolji ostvareni rezultat; ovaj izbor pravila treba potvrditi pre produkcije.
- Redovni K1 i K2 ne ulaze u limit. Nakon oba redovna događaja, najviše tri ponovljena izlaska **ukupno** za K1 i K2, po predmetu i školskoj godini.
- Profesor može da odobri dodatni izlazak za određenog studenta i događaj, uz obrazloženje. Odobrenje se može opozvati pre upisa rezultata.
- Položeni ispit se ručno potvrđuje uz datum i ispitni rok. Student se sklanja iz aktivne liste, a rezultati ostaju u bazi.
- Moguć je Excel izvoz i preuzimanje cele SQLite baze.

## Bezbednost i ograničenja

**Samo za izmišljene testne podatke.** Nema prijavljivanja ni kontrole prava pristupa. SQLite se lokalno čuva u `tf_matematika.db` i **nije trajna baza na Streamlit Community Cloud-u**. Pre stvarne upotrebe dodati autentifikaciju, zaštićenu upravljanu bazu, rezervne kopije, revizioni dnevnik i zaštitu ličnih podataka. Ne postavljati `.db` fajl na GitHub.

## GitHub

Kreirati privatni repozitorijum `tf-matematika`, postaviti `app.py`, `requirements.txt`, `README.md`, `.gitignore`, a u Streamlit-u izabrati `app.py` kao ulaznu datoteku.
