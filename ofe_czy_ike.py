# Environment
import pandas as pd
import numpy as np


class Pension:
    def __init__(self, r, inflacja, prognozowana_emerytura_brutto, ofe, kobieta, wiek):
        # Contant variables
        self.belka = 0.19
        self.podatek_od_prywatyzacji = 0.15
        self.stawka_pit = 0.17  # na emeryturze

        # Assumptions
        self.r = r  # stopa zwrotu z IKE, default=0.04
        self.inflacja = inflacja  # default=0.025
        self.waloryzacja_emerytur = inflacja + 0.20*0.04  # minimum to oficjalna infl. + 20% realnego wzrostu gosp.

        # User data
        self.prognozowana_emerytura_brutto = prognozowana_emerytura_brutto  # wartość nominalna
        self.ofe = ofe
        self.kobieta = kobieta
        self.wiek = wiek  # max 65 dla faceta i 60 dla kobiety
        
        # Placeholders
        self.efektywna_stawka_opodatkowania = None
        self.oczekiwana_dalsza_dlugosc_zycia = None  # spodziewane lata na emeryturze
        self.do_emerytury = None
        self.lat_na_emeryturze_wg_zus = None
        self.oczekiwana_liczba_lat_na_emeryturze = None
        self.waloryzacja = None

        # Wyniki
        self.projekcja_ike = None
        self.projekcja_zus = None
        self.suma_dodatku_od_ike = None
        self.suma_dodatku_od_zus = None

    def _efektywna_stawka_opodatkowania(self):
        # TODO [LOW] zmienny efektywny pit - (inflacja rośnie, to podatek się zmienia)
        skladka_zdrowotna = self.prognozowana_emerytura_brutto * 0.09
        zaliczka_pit = self.prognozowana_emerytura_brutto * self.stawka_pit - 556.02/12 - self.prognozowana_emerytura_brutto * 0.0775
        prognozowana_emerytura_netto = self.prognozowana_emerytura_brutto - skladka_zdrowotna - zaliczka_pit
        self.efektywna_stawka_opodatkowania = 1 - prognozowana_emerytura_netto / self.prognozowana_emerytura_brutto

    def _oczekiwana_dalsza_dlugosc_zycia(self):
        # https://stat.gov.pl/obszary-tematyczne/ludnosc/trwanie-zycia/trwanie-zycia-w-2018-r-,2,13.html
        life_expectancy = pd.read_csv('data/life_expectancy_gus_2018.csv')
        if self.kobieta == 0:
            life_exp = life_expectancy.loc[life_expectancy['age'] == self.wiek]['life_expectancy_m']
        elif self.kobieta == 1:
            life_exp = life_expectancy.loc[life_expectancy['age'] == self.wiek]['life_expectancy_f']
        else:
            life_exp = None
        self.oczekiwana_dalsza_dlugosc_zycia = np.round(float(life_exp))
    
    @staticmethod
    def _waloryzacja():
        # Historyczne wartości waloryzacji kapitału zgromadzonego w ZUS
        hist_waloryzacja = [1.1272, 1.0668, 1.0190, 1.0200, 1.0363, 1.0555, 1.0690, 1.1285, 1.1626, 1.0722, 1.0398,
                            1.0518, 1.0468, 1.0454, 1.0206, 1.0537, 1.0637, 1.0868, 1.0920]
        # mean_hist_waloryzacja = np.mean(hist_waloryzacja)
        # avg_geom_hist_waloryzacja = np.power(np.prod(hist_waloryzacja), 1/len(hist_waloryzacja))
        q40 = np.quantile(hist_waloryzacja, 0.4)
        # plt.plot([int(x) for x in range(2000, 2019)], hist_waloryzacja)
        # plt.title('Stopy waloryzacji kapitału zgromadzonego w ZUS')
        return q40

    def wariant_ike(self):
        # Etap 1: Do emerytury
        # w 1. roku spryw. OFE wartość kapitału spada o 7.5%, reszta pracuje na inwestycji w ramach IKE bez  Belki
        # w 2. roku wartość kapitału topnieje o kolejne 7.5%, ale pracuje na inwestycji w ramach IKE bez podatku Belki
        # w 3. i każdym kolejnym roku do emerytury wartość kapitału rośnie o oczekiwaną stopę zwrotu, bez podatku Belki
        npv_ike = self.ofe * (1 - self.podatek_od_prywatyzacji / 2) * (1 + self.r) * (1 - self.podatek_od_prywatyzacji / 2) * (1 + self.r) * np.power((1 + self.r), self.do_emerytury - 2)

        # W momencie wypłaty środków z IKE ich wartość realna zjadana jest przez inflację,
        # toteż wartość nominalna > realna. Deflator:
        npv_ike = npv_ike / np.power((1 + self.inflacja), self.do_emerytury)
        print("Zgromadzony kapitał na IKE w momencie przejścia na emeryturę wynosi %d PLN na dzisiejsze pieniądze "
              "(po opodatkowaniu i w cenach z dzisiaj)" % npv_ike)

        # Etap 2: Po emeryturze
        projekcja_ike = pd.Series(range(1, self.oczekiwana_liczba_lat_na_emeryturze + 1), name='rok_emerytury').to_frame()

        npv_ike_dyn = npv_ike
        npv_ike_list = list()
        kapital_rok = list()

        # Zakładamy, że na emeryturze kapitał pracuje nam na bezpiecznej lokacie (opodatkowanej podatkiem Belki)
        for rok in range(self.oczekiwana_liczba_lat_na_emeryturze):
            # Kapitał wypłacamy sobie proporcjonalnie do pozostałych lat na emeryturze - np. pozostało nam (stat.)
            # 5 lat, więc wypłacamy sobie 1/5 tego co zostało
            kapital_rok.append(npv_ike_dyn / (self.oczekiwana_liczba_lat_na_emeryturze - rok))
            # w międzyczasie, kapitał, który pozostał inwestujemy, ale zżera go nam też inflacja
            # TODO niższe r na emeryturze
            npv_ike_dyn = (npv_ike_dyn - npv_ike_dyn / (self.oczekiwana_liczba_lat_na_emeryturze - rok)) * (1 + self.r * (1 - self.belka)) / (1 + self.inflacja)
            npv_ike_list.append(npv_ike_dyn)

        projekcja_ike['npv_ike'] = npv_ike_list
        projekcja_ike['kapital_rok'] = kapital_rok
        projekcja_ike['ike_dodatek_emerytura'] = round(projekcja_ike['kapital_rok'] / 12, 2)

        self.projekcja_ike = projekcja_ike

        print("Efekt wybrania prywatyzacji:")
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
        npv_zus = self.ofe * np.power(self.waloryzacja, self.do_emerytury) / np.power((1 + self.inflacja), self.do_emerytury)

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
            npv_zus_dyn = (npv_zus_dyn - npv_zus_dyn / (self.lat_na_emeryturze_wg_zus - rok)) * (1 + self.waloryzacja_emerytur) / (1 + self.inflacja)
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

        if self.suma_dodatku_od_zus > self.suma_dodatku_od_ike:
            print("Wybranie ZUS zaowocuje średnio o {}% wyższym dodatkiem do emerytury".format(stosunek_zus_do_ike))
        elif self.suma_dodatku_od_zus < self.suma_dodatku_od_ike:
            print("Wybranie IKE zaowocuje średnio o {}% wyższym dodatkiem do emerytury".format(stosunek_ike_do_zus))
        else:
            print("ganz egal")

    def main(self):
        # Prepare all variables
        self._efektywna_stawka_opodatkowania()
        self._oczekiwana_dalsza_dlugosc_zycia()
        self.do_emerytury = 65 - 5*self.kobieta - self.wiek
        self.lat_na_emeryturze_wg_zus = 18 + 5 * self.kobieta  # https://www.money.pl/emerytury/emerytury-gus-ma-jednoczesnie-dobra-i-zla-wiadomosc-dane-dotycza-sredniej-dlugosci-zycia-6363469538014849a.html
        self.oczekiwana_liczba_lat_na_emeryturze = int(self.wiek + self.oczekiwana_dalsza_dlugosc_zycia - 65 + 5 * self.kobieta)
        self.waloryzacja = self._waloryzacja()
        # Compute IKE
        self.wariant_ike()
        self.wariant_zus()
        self.podsumowanie()
        

p = Pension(r=0.04, inflacja=0.025, prognozowana_emerytura_brutto=1200, ofe=11500, kobieta=0, wiek=52)
p.main()
