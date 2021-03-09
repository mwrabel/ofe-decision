# Environment
import pandas as pd
import numpy as np


class Pension:
    def __init__(self, r, r_em, inflacja, prognozowana_emerytura_brutto, ofe, kobieta, wiek,
                 zmiana_wartosci_jednostki_ofe, stawka_pit):
        # Contant variables
        self.belka = 0.19
        self.podatek_od_prywatyzacji = 0.15

        # Assumptions
        self.r = r  # nominalna stopa zwrotu z IKE przed emeryturą, default=0.05
        self.r_em = r_em  # nominalna stopa zwrotu z IKE w czasie emerytury, default=0.02
        self.inflacja = inflacja  # default=0.025
        self.zmiana_wartosci_jednostki_ofe = zmiana_wartosci_jednostki_ofe
        self.stawka_pit = stawka_pit  # na emeryturze 0.17

        # User data
        self.prognozowana_emerytura_brutto = prognozowana_emerytura_brutto  # wartość nominalna
        self.ofe = ofe
        self.kobieta = kobieta
        self.wiek = wiek  # max 65 dla faceta i 60 dla kobiety

        # Computations
        self.efektywna_stawka_opodatkowania = None
        self._efektywna_stawka_opodatkowania()
        self.oczekiwana_dalsza_dlugosc_zycia = None  # spodziewane lata na emeryturze
        self._oczekiwana_dalsza_dlugosc_zycia()

        # Precomputations
        self.do_emerytury = 65 - 5*self.kobieta - self.wiek
        self.lat_na_emeryturze_wg_zus = 18 + 5 * self.kobieta  # TODO dodać zmienność
        # https://www.money.pl/emerytury/emerytury-gus-ma-jednoczesnie-dobra-i-zla-wiadomosc-dane-dotycza-sredniej-dlugosci-zycia-6363469538014849a.html
        self.oczekiwana_liczba_lat_na_emeryturze = int(self.wiek + self.oczekiwana_dalsza_dlugosc_zycia - 65 + 5 * self.kobieta)
        self.waloryzacja_kapitalu = self._waloryzacja(param='kapital')
        self.waloryzacja_emerytur = self._waloryzacja(param='emerytura')  # minimum to oficjalna infl. + 20% realnego wzrostu gosp. mierzonego wzrostem zarobków + bonus od rządu

        # Wyniki
        self.projekcja_ike = None
        self.projekcja_zus = None
        self.suma_dodatku_od_ike = None
        self.suma_dodatku_od_zus = None
        self.rekomendacja_komentarz = None
        self.rekomendacja_przewaga = None
        self.sredni_dodatek_do_emerytury_ike = None
        self.sredni_dodatek_do_emerytury_zus = None

    def _efektywna_stawka_opodatkowania(self):
        # TODO [LOW] zmienny efektywny pit - (inflacja rośnie, to podatek się zmienia)
        # TODO zmienny PIT - ruchoma kwota wolna od podatku
        skladka_zdrowotna = self.prognozowana_emerytura_brutto * 0.09
        zaliczka_pit = self.prognozowana_emerytura_brutto * self.stawka_pit - 525.12/12 - self.prognozowana_emerytura_brutto * 0.0775
        prognozowana_emerytura_netto = self.prognozowana_emerytura_brutto - skladka_zdrowotna - zaliczka_pit
        self.efektywna_stawka_opodatkowania = 1 - prognozowana_emerytura_netto / self.prognozowana_emerytura_brutto

    def _oczekiwana_dalsza_dlugosc_zycia(self):
        # https://stat.gov.pl/obszary-tematyczne/ludnosc/trwanie-zycia/trwanie-zycia-w-2019-roku,2,14.html

        # m
        ogomez = pd.read_excel('data/tablica_a._tablica_trwania_zycia_2019.xlsx', header=5, sheet_name='ogomez', engine='openpyxl')
        ogomez = ogomez.rename(columns={'Unnamed: 0': 'age', 'Unnamed: 6': 'life_expectancy_m'})
        ogomez = ogomez[['age', 'life_expectancy_m']]
        ogomez = ogomez.set_index('age')

        # k
        ogokob = pd.read_excel('data/tablica_a._tablica_trwania_zycia_2019.xlsx', header=5, sheet_name='ogokob', engine='openpyxl')
        ogokob = ogokob.rename(columns={'Unnamed: 0': 'age', 'Unnamed: 6': 'life_expectancy_f'})
        ogokob = ogokob[['age', 'life_expectancy_f']]
        ogokob = ogokob.set_index('age')

        life_expectancy = ogomez.join(ogokob, how='left').reset_index()

        if self.kobieta == 0:
            life_exp = life_expectancy.loc[life_expectancy['age'] == self.wiek]['life_expectancy_m']
        elif self.kobieta == 1:
            life_exp = life_expectancy.loc[life_expectancy['age'] == self.wiek]['life_expectancy_f']
        else:
            life_exp = None
        self.oczekiwana_dalsza_dlugosc_zycia = np.round(float(life_exp))

    @staticmethod
    def _waloryzacja(param='kapital'):
        # Historyczne wartości waloryzacji kapitału zgromadzonego w ZUS od 2001 do 2020
        hist_waloryzacja_kapitalu = [
            1.1272, 1.0668, 1.0190, 1.0200, 1.0363, 1.0555, 1.0690, 1.1285, 1.1626, 1.0722, 1.0398, 1.0518, 1.0468,
            1.0454, 1.0206, 1.0537, 1.0637, 1.0868, 1.0920, 1.0894
        ]
        # mean_hist_waloryzacja = np.mean(hist_waloryzacja)
        # avg_geom_hist_waloryzacja = np.power(np.prod(hist_waloryzacja), 1/len(hist_waloryzacja))
        # plt.plot([int(x) for x in range(2000, 2019)], hist_waloryzacja)
        # plt.title('Stopy waloryzacji kapitału zgromadzonego w ZUS')

        # Historyczne wartości inflacji emeryckiej 2013-2020
        hist_inflacja_w_gosp_emer = [1.011, 1.000, 0.994, 0.996, 1.023, 1.018, 1.026, 1.039]

        # Historyczne wartości waloryzacji emerytury ZUS od 2000 do 2020
        # uwaga: 2005 waloryzacja wstrzymana
        # uwaga: 2007 wpisano 1.045, ale było 71zł brutto dla każdego
        # uwaga: 2015 nie mniej niż 36zł brutto
        # uwaga: 2017 nie mniej niż 10zł brutto
        hist_waloryzacja_emerytury = [
            1.0750,
            1.1270, 1.0700, 1.0370, 1.0180, 1.0000, 1.0620, 1.0450, 1.0650, 1.0610, 1.0462,
            1.0310, 1.0000, 1.0400, 1.0160, 1.0068, 1.0024, 1.0044, 1.0298, 1.0268, 1.0356,
            1.0424
        ]
        if param == 'kapital':
            q50 = np.quantile(hist_waloryzacja_kapitalu, 0.5)
        elif param == 'emerytura':
            q50 = np.quantile(hist_waloryzacja_emerytury, 0.5)
        else:
            q50 = np.nan

        return q50

    def wariant_ike(self):
        # Etap 1: Do emerytury
        # w 1. roku spryw. OFE wartość kapitału spada o 70%*15%, reszta pracuje na inwestycji w ramach IKE bez  Belki
        # w 2. roku wartość kapitału topnieje o kolejne 30%*15%, ale pracuje na inwestycji w ramach IKE bez podatku Belki
        # w 3. i każdym kolejnym roku do emerytury wartość kapitału rośnie o oczekiwaną stopę zwrotu, bez podatku Belki
        npv_ike = self.ofe * (1 - self.podatek_od_prywatyzacji*0.7) * (1 + self.r) * (1 - (self.podatek_od_prywatyzacji*0.3)/(1-self.podatek_od_prywatyzacji)) * (1 + self.r) * np.power((1 + self.r), self.do_emerytury - 2)  # TODO co jak do emerytury jest mniej niż dwa lata

        # W momencie wypłaty środków z IKE ich wartość realna zjadana jest przez inflację,
        # toteż wartość nominalna > realna. Deflator:
        npv_ike = npv_ike / np.power((1 + self.inflacja), self.do_emerytury)
        print("Zgromadzony kapitał na IKE w momencie przejścia na emeryturę wynosi %d PLN na dzisiejsze pieniądze "
              "(po opodatkowaniu)" % npv_ike)

        # Etap 2: Po przejściu na emeryturę
        projekcja_ike = pd.Series(range(1, self.oczekiwana_liczba_lat_na_emeryturze + 1), name='rok_emerytury').to_frame()

        npv_ike_dyn = npv_ike
        npv_ike_list = list()
        kapital_rok = list()

        # Zakładamy, że na emeryturze kapitał pracuje nam na bezpiecznej lokacie (opodatkowanej podatkiem Belki)
        for rok in range(self.oczekiwana_liczba_lat_na_emeryturze):
            # Kapitał wypłacamy sobie proporcjonalnie do pozostałych lat na emeryturze - np. pozostało nam (stat.)
            # 5 lat, więc wypłacamy sobie 1/5 tego co zostało
            wyplata_z_ike = npv_ike_dyn / (self.oczekiwana_liczba_lat_na_emeryturze - rok)
            kapital_rok.append(wyplata_z_ike)
            # w międzyczasie, kapitał, który pozostał inwestujemy, ale zżera go nam też inflacja
            npv_ike_dyn = (npv_ike_dyn - wyplata_z_ike) * (1 + self.r_em * (1 - self.belka)) / (1 + self.inflacja)
            npv_ike_list.append(npv_ike_dyn)

        projekcja_ike['npv_ike'] = npv_ike_list
        projekcja_ike['kapital_rok'] = kapital_rok
        projekcja_ike['ike_dodatek_emerytura'] = round(projekcja_ike['kapital_rok'] / 12, 2)

        self.projekcja_ike = projekcja_ike

        print("Efekt wybrania prywatyzacji: ")
        print("W pierwszym roku emerytury zwiększy nam emeryturę o {} PLN".format(projekcja_ike['ike_dodatek_emerytura'].iloc[0]))
        print("W {}. roku emerytury zwiększy nam emeryturę o {} PLN".format(projekcja_ike.shape[0], projekcja_ike['ike_dodatek_emerytura'].iloc[projekcja_ike.shape[0] - 1]))
        print("Jeśli umrzemy wcześniej niż średnia, wtedy niewykorzystany kapitał jest dziedziczony")
        print("Jeśli przeżyjemy dłużej niż średnia, po wyczerpaniu środków z IKE emerytura wraca do bazowej wielkości")
        print("Szanse: wyższy zwrot z inwestycji, niższa inflacja, zmiana zasad pobierania podatku Belki na bardziej korzystne dla konsumentów")
        print("Zagrożenia: Ponowna grabież środków tym razem z ike, kiepskie inwestycje, wysoka inflacja, podwyżka podatku Belki")

    def wariant_zus(self):
        # Etap 1: Do emerytury
        # Środki z OFE zostają przekazane do ZUS, gdzie korzystają z corocznej waloryzacji kapitału, 
        # która historycznie była wysoka, warto wspomnieć iż zeszłoroczna waloryzacja była wyższa niż średnia.
        # Do obliczeń założymy konserwatywnie nie średnią, ani nie medianę (jeszcze niższa), tylko 40 percentyl 
        # od 2000 roku (nie mogłem dokopać się do wcześniejszych danych)
        # Stopa waloryzacji jest pochodną rozwoju gospodarczego, założenie 40 percentyla to założenie realistyczne
        # Środki z OFE zapisane są na konto w ZUS, są waloryzowane co roku, aż do momentu przejścia na emeryturę.
        # Ich realna wartość będzie nieco zmniejszona przez inflację, co też jest uwzględnione

        # cena jednostki OFE nie może być mniejsza, niż wartość tej jednostki na dzień 15 kwietnia 2019
        # https://subiektywnieofinansach.pl/koronawirus-znow-zaatakowal-oszczednosci-polakow-ceny-akcji-najnizsze-od-pieciu-lat-ale-rzad-moze-wyrowna-spadki-ofe/

        npv_zus = np.max([1/(1+self.zmiana_wartosci_jednostki_ofe) * self.ofe, self.ofe]) * np.power(self.waloryzacja_kapitalu, self.do_emerytury) / np.power((1 + self.inflacja), self.do_emerytury)

        # Uwaga: od tego kapitału będzie trzeba zapłacić podatek
        print("Zgromadzony kapitał na ZUS w momencie przejścia na emeryturę wynosi %d PLN na dzisiejsze pieniądze "
              "(przed opodatkowaniem)" % npv_zus)

        # kontynuacja: co po emeryturze?
        projekcja_zus = pd.Series(range(1, self.lat_na_emeryturze_wg_zus + 1), name='rok_emerytury').to_frame()

        # Zakładamy, że na emeryturze kapitał już nie jest waloryzowany. Zamiast tego waloryzowana jest emerytura
        # Waloryzacja emerytury historycznie była zauważalnie niższa niż waloryzacja kapitału, dlatego tutaj
        # przyjmujemy znacznie mniejsze wartości. Dobra wiadomość jest taka, że waloryzacja emerytury nie może być
        # niższa niż stopa inflacji statystycznego gospodarstwa emerytów powiększona o chyba 20% wzrostu gospodarczego.
        # Tutaj wracamy do wartości nominalnej, bo od niej liczy się podatek
        npv_zus_dyn = npv_zus * np.power((1 + self.inflacja), self.do_emerytury)
        npv_zus_list = list()
        kapital_rok = list()
        for rok in range(self.lat_na_emeryturze_wg_zus):
            # Emerytura jest obliczona w taki sposób, że ZUS wypłaca nam nasz kapitał proporcjonalnie do spodziewanej
            # dlugosci zycia Polaka w wieku 65 lat, bez rozróżnienia na płeć.
            # Tutaj używamy wartości nominalnych, by móc poprawnie wyliczyć efektywny PIT)
            # A POTEM ponownie stosujemy deflator sprzed emerytury by wrócić do wartości realnych
            kapital_rok.append(npv_zus_dyn / (self.lat_na_emeryturze_wg_zus - rok) * (1 - self.efektywna_stawka_opodatkowania) / np.power((1 + self.inflacja), self.do_emerytury))
            # w międzyczasie, kapitał, który pozostał inwestujemy, ale zżera go nam też inflacja
            npv_zus_dyn = (npv_zus_dyn - npv_zus_dyn / (self.lat_na_emeryturze_wg_zus - rok)) * self.waloryzacja_emerytur / (1 + self.inflacja)
            npv_zus_list.append(npv_zus_dyn)

        projekcja_zus['npv_zus'] = npv_zus_list
        projekcja_zus['kapital_rok'] = kapital_rok
        projekcja_zus['zus_dodatek_emerytura'] = round(projekcja_zus['kapital_rok'] / 12, 2)

        print("Efekt wybrania ZUSu:")
        print("W pierwszym roku emerytury zwiększy nam emeryturę o {} PLN".format(projekcja_zus['zus_dodatek_emerytura'].iloc[0]))
        print("Jeśli umrzemy wcześniej, wtedy niewykorzystany kapitał nie jest dziedziczony")
        print("Jeśli przeżyjemy dłużej, po wyczerpaniu środków emerytura dalej jest waloryzowana o stopę nieco wyższą niż inflacja")
        print("Szanse: podwyższenie kwoty wolnej od podatku, obniżenie PIT, przeciętny lub dobry rozwój gospodarki Polski")
        print("Zagrożenia: Ustawowe obniżenie emerytur, zawieszenie lub zmiana zasad waloryzacji kapitału, problemy z ZUS")

        projekcja_zus_przez_pryzmat_oczekiwanej_dlugosci_zycia = pd.Series(range(1, self.oczekiwana_liczba_lat_na_emeryturze + 1), name='rok_emerytury').to_frame()
        empiryczna_waloryzacja = (projekcja_zus['zus_dodatek_emerytura'] / projekcja_zus['zus_dodatek_emerytura'].shift(1))[1:].mean()
        zus_dodatek_emerytura = [np.round(projekcja_zus['zus_dodatek_emerytura'][0] * np.power(empiryczna_waloryzacja, x), 2) for x in range(self.oczekiwana_liczba_lat_na_emeryturze)]
        projekcja_zus_przez_pryzmat_oczekiwanej_dlugosci_zycia['zus_dodatek_emerytura'] = zus_dodatek_emerytura
        self.projekcja_zus = projekcja_zus_przez_pryzmat_oczekiwanej_dlugosci_zycia
        
    def podsumowanie(self):
        # Porównanie OFE->IKE vs. OFE->ZUS
        # plt.plot(projekcja_ike['rok_emerytury'], projekcja_ike['ike_dodatek_emerytura'])
        # plt.plot(projekcja_zus_przez_pryzmat_oczekiwanej_dlugosci_zycia['rok_emerytury'], projekcja_zus_przez_pryzmat_oczekiwanej_dlugosci_zycia['zus_dodatek_emerytura'])
        # plt.title('Dodatkowe pieniądze na emeryturę (po opodatkowaniu)')
        # plt.legend()
        # plt.ylim(0)
        self.suma_dodatku_od_ike = sum(self.projekcja_ike['ike_dodatek_emerytura']) * 12
        self.suma_dodatku_od_zus = sum(self.projekcja_zus['zus_dodatek_emerytura']) * 12

        stosunek_zus_do_ike = round((self.suma_dodatku_od_zus / self.suma_dodatku_od_ike - 1) * 100, 1)
        stosunek_ike_do_zus = round((self.suma_dodatku_od_ike / self.suma_dodatku_od_zus - 1) * 100, 1)

        self.sredni_dodatek_do_emerytury_ike = np.round(self.suma_dodatku_od_ike / 12 / self.oczekiwana_liczba_lat_na_emeryturze, 2)
        self.sredni_dodatek_do_emerytury_zus = np.round(self.suma_dodatku_od_zus / 12 / self.oczekiwana_liczba_lat_na_emeryturze, 2)

        if self.suma_dodatku_od_zus > self.suma_dodatku_od_ike:
            print("Wybranie ZUS zaowocuje średnio o {}% wyższym dodatkiem do emerytury".format(stosunek_zus_do_ike))
            self.rekomendacja_komentarz = 'ZUS'
            self.rekomendacja_przewaga = stosunek_zus_do_ike
        elif self.suma_dodatku_od_zus < self.suma_dodatku_od_ike:
            print("Wybranie IKE zaowocuje średnio o {}% wyższym dodatkiem do emerytury".format(stosunek_ike_do_zus))
            self.rekomendacja_komentarz = 'IKE'
            self.rekomendacja_przewaga = stosunek_ike_do_zus
        else:
            print("ganz egal")

    def main(self):
        self.wariant_ike()
        self.wariant_zus()
        self.podsumowanie()
        

# p = Pension(r=0.05, r_em=0.02, inflacja=0.025, prognozowana_emerytura_brutto=2200, ofe=11500, kobieta=0, wiek=52,
#             zmiana_wartosci_jednostki_ofe=-0.30)
# p.main()
