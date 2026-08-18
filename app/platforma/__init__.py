"""PLATFORMA BOSHQARUVI — mijozlar, obuna, AI sarfi.

Bu paket MIJOZ bazasidan ATAYLAB ajratilgan. Sabab: mijoz bazasida
`Base.metadata.create_all()` chaqirilganda bu jadvallar u yerda paydo
bo'lmasligi kerak — aks holda har mijozning bazasida boshqa
mijozlarning ro'yxati turardi.

Shuning uchun bu yerda alohida `BoshqaruvBase` bor.
"""
