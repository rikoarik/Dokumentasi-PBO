
import kivy
kivy.require('1.9.0')

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Line, Triangle
from kivy.properties import (
    NumericProperty, BooleanProperty, ObjectProperty
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.widget import Widget
from kivy.vector import Vector

from collections import defaultdict
from datetime import date, datetime
from functools import partial
from itertools import chain, cycle
import math
import random

############################################################################

config = {}
try:
    import config as _conf
except ImportError:
    _conf = None

config['fonts'] = getattr(_conf, 'fonts', {})
config['roman_numerals'] = getattr(_conf, 'roman_numerals', (
    'I', 'II', 'III', 'IV', 'V', 'VI',
    'VII', 'VIII', 'IX', 'X', 'XI', 'XII'
))
config['minus_sign'] = getattr(_conf, 'minus_sign', '-')
config['em_dash'] = getattr(_conf, 'em_dash', '-')
config['date_separator'] = getattr(_conf, 'date_separator', '/')
_conf_colors = getattr(_conf, 'colors', {})

# Warna data. Idenya adalah elemen tampilan yang mewakili
# informasi yang sama dengan cara tertentu harus diwarnai sama untuk membuatnya
# lebih mudah melihat hubungan. Kami membutuhkan data dalam dua berbeda
# format sehingga paling mudah untuk menghitung keduanya dari desimal tunggal
# representasi.
_colors_d = {
    'hour':     (255,   0,   0),
    'minute':   (  0, 255,   0),
    'second':   (  0,   0, 255),
    'ampm':     (255, 255,   0),
    'dayname':  ( 95, 255, 175),
    'day':      (255, 175,  95),
    'month':    (175,  95, 255),
    'year':     (255,  95, 175),
    'on':       (175, 175, 175),
    'off':      ( 71,  71,  71),
    'high':     (255, 255, 255),
    'rim':      (255, 255, 255),
    'rim_text': (255, 255, 255),
    'numerals': (255, 255, 255)
}

for k in _colors_d.keys():
    if k in _conf_colors:
        _colors_d[k] = _conf_colors[k]

# Populasikan dua dicts lainnya dengan float dan heksadesimal yang dihitung
# nilai string.
_colors_f = {}
_colors_h = {}

for k, v in _colors_d.items():
    _colors_f[k] = (v[0]/255, v[1]/255, v[2]/255)
    _colors_h[k] = "{:02x}{:02x}{:02x}".format(*v)

config['colors'] = _colors_f

# Pintasan untuk mendapatkan tag [warna] (untuk teks label) dari data di atas.
def _c(k, s):
    return "[color={0}]{1}[/color]".format(_colors_h[k], s)

# Kemudian pintas selanjutnya karena akan menjadi sangat berulang jika tidak.
_c_H = partial(_c, 'hour')
_c_M = partial(_c, 'minute')
_c_S = partial(_c, 'second')
_c_am = partial(_c, 'ampm')
_c_D = partial(_c, 'dayname')
_c_d = partial(_c, 'day')
_c_m = partial(_c, 'month')
_c_y = partial(_c, 'year')
_c_on = partial(_c, 'on')
_c_off = partial(_c, 'off')
_c_high = partial(_c, 'high')

# Nomor teks untuk jam kata, dalam pasangan (huruf besar, huruf kecil).
num_strings = list(
    map(lambda s: (s.capitalize(), s), (
        "zero", "one", "two", "three", "four", "five", "six", "seven",
        "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
        "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"
    )
))

for stem in "twenty", "thirty", "forty", "fifty":
    stem_ = stem.capitalize()
    num_strings.append((stem_, stem))
    num_strings += [(stem_+'-'+s[1],stem+'-'+s[1]) for s in num_strings[1:10]]


############################################################################

class HourLabel(Label):
    """
    Merupakan salah satu angka di sekitar jam wajah.
    """
    hour = NumericProperty(0)
    roman = BooleanProperty(False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hour, self._radius = None, None

    def pos_offset(self):
        """
        Kembalikan vektor yang menggambarkan di mana label harus diposisikan,
        relatif terhadap pusat jam, menurut jamnya
        atribut.
        """
        hour, radius = self.hour, self.parent.radius
        if (hour, radius) != (self._hour, self._radius):
            self._hour = hour
            self._radius = radius
            angle = -30 * hour
            self._pos_offset = Vector(0, 0.85*radius).rotate(angle)

        return self._pos_offset

    def update(self, *args):
        """
       Perbarui teks dan posisi label agar sesuai dengan atributnya.
        """
        if self.roman:
            self.text = config['roman_numerals'][self.hour-1]
        else:
            self.text = str(self.hour)

        offset = self.pos_offset()
        self.center_x = self.parent.width/2 + offset.x
        self.center_y = self.parent.height/2 + offset.y

    on_roman = on_hour = update

############################################################################

class DigitalTime(Label):
    """
    Kelas dasar untuk tampilan jam digital.
    """
    def update(self, h, m, s):
        raise NotImplementedError(
            "You must implement this method in a subclass."
        )

class DigitalTime24(DigitalTime):
    """
    Tampilan jam digital 24 jam, dengan detik.
    """
    def _fmt(k):
        return ''.join((
            _c_H('{:02d}'), _c(k,':'),
            _c_M('{:02d}'), _c(k,':'),
            _c_S('{:02d}')
        ))

    fmt = (_fmt('on'), _fmt('off'))

    def update(self, h, m, s):
        """
        Perbarui tampilan ke waktu baru.
        """
        self.text = self.fmt[s % 2].format(h, m, s)

class DigitalTime12(DigitalTime):
    """
    Tampilan jam digital 12 jam, tanpa detik.
    """
    def _fmt(k):
        return ''.join((
            _c_H('{:d}'), _c(k,':'),
            _c_M('{:02d}'), _c_am('{:s}')
        ))

    fmt = (_fmt('on'), _fmt('off'))

    def update(self, h, m, s):
        """
        Perbarui tampilan ke waktu baru.
        """
        if h >= 12:
            ampm = "pm"
            h -= 12
        else:
            ampm = "am"

        if h == 0:
            h = 12

        self.text = self.fmt[s % 2].format(h, m, ampm)

############################################################################

class ClockHand(Widget):
    """
    Kelas dasar untuk jarum jam.
    """
    alpha = 0.6
    rim_text = ObjectProperty(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hand = None
        self.angle = 0

    def points(self):
        """
        Hitung poin yang dibutuhkan untuk menggambar tangan pada saat ini
        sudut.
        """
        rotated = [ v.rotate(self.angle) for v in self.point_vectors ]

        # Indeks 0 adalah titik luar, sedangkan yang lain berada di
        #ujung gelendong.
        rotated[0] *= self.parent.radius
        for r in rotated[1:]:
            r *= self.parent.min_wh() / 60

        # Tambahkan offset tengah, konversikan dari daftar vektor ke a
        # daftar datar, dan bulatkan ke nilai integer untuk menghindari gangguan
        # efek aliasing.
        center = (self.parent.width/2, self.parent.height/2)
        points = map(int, chain.from_iterable(
            [ v+center for v in rotated ]
        ))

        return list(points)

    def update(self, value):
        """
        Perbarui tangan ke nilai yang ditentukan.
        """
        self.angle = -value * self.unit_angle
        if self.hand is not None:
            points = self.points()
            self.hand.points = points

            # Perbarui label pada pelek jam
            center = (self.parent.width/2, self.parent.height/2)
            v = Vector(0, 1).rotate(self.angle)
            v *= self.parent.radius * 1.1
            self.rim_text.center = v + center
            self.rim_text.text = "{0:02d}".format(math.floor(value))

    def construct(self):
        """
        Buat instruksi untuk menggambar tangan.
        """
        with self.canvas.after:
            Color(
                self.color[0], self.color[1], self.color[2], self.alpha,
                mode='rgba'
            )
            self.hand = Triangle(points=self.points())

class HourHand(ClockHand):
    """
    Merupakan jarum jam.
    """
    unit_angle = 30
    point_vectors = (Vector(0, 0.6), Vector(-1, -2), Vector(1, -2))
    color = _colors_f['hour']

class MinuteHand(ClockHand):
    """
    Merupakan jarum menit.
    """
    unit_angle = 6
    point_vectors = (Vector(0, 0.95), Vector(-0.5, -2), Vector(0.5, -2))
    color = _colors_f['minute']

class SecondHand(ClockHand):
    """
    Merupakan tangan kedua.
    """
    unit_angle = 6
    point_vectors = (Vector(0, 0.95), Vector(-0.25, -2), Vector(0.25, -2))
    color = _colors_f['second']

############################################################################

class ClockFace(RelativeLayout):
    """
    Tampilan jam analog.
    """
    radius = NumericProperty(0)

    def __init__(self, *args, **kwargs):
        self.hour_labels = []
        super().__init__(*args, **kwargs)

    def min_wh(self):
        return min(self.width, self.height)

    def update(self, hours, minutes, seconds, microseconds):
        """
        Perbarui semua jarum jam ke nilai yang ditentukan.
        """
        # Kami ingin nilai fraksional untuk jarum jam dan menit begitu
        # Bahwa mereka menampilkan posisi di antara yang benar.
        s = seconds + microseconds/1000000
        m = minutes + s/60
        h = hours % 24 + m/60

        self.hour_hand.update(h)
        self.minute_hand.update(m)

        # Namun, untuk tangan kedua kita tetap menggunakan bilangan bulat
        # untuk mendapatkan tanda centang yang terlihat.
        self.second_hand.update(seconds)

    def update_hour_labels(self, *args):
        """
        Panggil metode pembaruan pada semua label jam.
        """
        for hl in self.hour_labels:
            hl.update()

    def flip_next_hour_label(self, seq, flip_to, *args):
        """
        Telepon balik. Membalik label berikutnya secara berurutan.
        """
        hour = next(seq)
        hl = self.hour_labels[hour]
        hl.roman = flip_to
        return hour < 11

    def flip_hour_labels(self, *args):
        """
        Kick off urutan membalik label jam dari desimal
        ke nomor Romawi, atau sebaliknya.
        """
        seq = iter(range(0,12))
        flip_to = not self.hour_labels[0].roman

        # Instansiasi parsial dari fungsi callback pada dasarnya
        # membuat penutupan di sekitar variabel di atas.
        fn = partial(self.flip_next_hour_label, seq, flip_to)
        Clock.schedule_interval(fn, 0.05)

        # Schedule the next flip sequence after a random interval.
        interval = random.randint(20,700)/100
        Clock.schedule_once(self.flip_hour_labels, interval)
        return True

    def start(self):
        """
        Inisialisasi dan mulai jam analog.
        """
        # Ini rapuh karena menganggap benda-benda tersebut terkandung
        # langsung di tata letak. Namun, itu sederhana.
        for c in self.children:
            if isinstance(c, HourLabel):
                self.hour_labels.append(c)
            elif isinstance(c, HourHand):
                self.hour_hand = c
            elif isinstance(c, MinuteHand):
                self.minute_hand = c
            elif isinstance(c, SecondHand):
                self.second_hand = c

                # Urutkan label jam ke dalam urutan numerik.
        self.hour_labels = sorted(self.hour_labels, key=lambda h:h.hour)

        # Label awalnya diatur sepenuhnya transparan untuk menghindari
        # Flash menjengkelkan dari mereka yang awalnya di tempat yang salah.
        for hl in self.hour_labels:
            hl.update()
            hl.opacity = 1

        self.hour_hand.construct()
        self.minute_hand.construct()
        self.second_hand.construct()

        # Jadwalkan peralihan pertama Anda dari angka desimal ke angka Romawi.
        Clock.schedule_once(self.flip_hour_labels, 7)

    def on_size(self, *args):
        Clock.schedule_once(self.update_hour_labels, -1)

############################################################################

class WordClock(Label):
    """
    Jam menampilkan waktu dalam kata-kata bahasa Inggris.
    """
    # Beberapa singkatan atas nama KERING.
    Hh = _c_H("{h}")
    Hh_ = _c_H("{h_}")
    HH = _c_H("{H}")
    past = _c_on(" past ") + Hh
    to = _c_on(" to ") + Hh_

    # Buat tabel dengan teks untuk setiap menit dalam jam, diinisialisasi
    # dengan versi generik yang sesuai sehingga kami tidak harus menentukannya
    # semua.
    _m_past = _c_M("{M}") + _c_on(" minutes past ") + Hh
    _m_to = _c_M("{M_}") + _c_on(" minutes to ") + Hh_
    time_strings = [_m_past]*30 + [_m_to]*30

    _m_after = ' '.join((
        _c_M("{MM}"), _c_on("minutes after"),
        _c_H("{HH}"), _c_on("o'clock"), _c_off(config['em_dash']),
        _c_high("60 "+config['minus_sign']), _c_M("{MM}"),
        _c_high("="), _c_M("{MM_}")
    ))

    _m_until = ' '.join((
        _c_high("60 "+config['minus_sign']), _c_M("{MM}"),
        _c_high("="), _c_M("{MM_}"), _c_on("minutes until"),
        _c_H("{HH_}"), _c_on("o'clock")
    ))

    alt_time_strings = [''] + [_m_until]*29 + [_m_after]*30

    # Teks untuk (hampir) pada jam tersebut.
    time_strings[0] = ' '.join((_c_H("{H}"), _c_M("o'clock")))
    time_strings[1] = ' '.join((
        _c_on("Just gone"), Hh, _c_M("o'clock")
    ))
    time_strings[59] = ' '.join((
        _c_on("Almost"), Hh_, _c_M("o'clock")
    ))

    # Dan juga untuk seperempat jam.
    time_strings[15] = _c_M("Quarter past") + " " + Hh
    time_strings[45] = _c_M("Quarter to")   + " " + Hh_
    time_strings[30] = _c_M("Half past")    + " " + Hh
    time_strings[29] = _c_on("Almost ")     + _c_M("half past") + " " + Hh
    time_strings[31] = _c_on("Just gone ")  + _c_M("half past") + " " + Hh

    # Versi yang dieja untuk interval 5 menit tersisa.
    time_strings[5]  = _c_M("Five")        + past
    time_strings[10] = _c_M("Ten")         + past
    time_strings[20] = _c_M("Twenty")      + past
    time_strings[25] = _c_M("Twenty-five") + past
    time_strings[35] = _c_M("Twenty-five") + to
    time_strings[40] = _c_M("Twenty")      + to
    time_strings[50] = _c_M("Ten")         + to
    time_strings[55] = _c_M("Five")        + to

    # Teks untuk bit "in the sore".
    _midnight  = _c_am("midnight")
    _night     = ' '.join( (_c_on("at"), _c_am("night")) )
    _evening   = ' '.join( (_c_on("in the"), _c_am("evening")) )
    _afternoon = ' '.join( (_c_on("in the"), _c_am("afternoon")) )
    _midday    = _c_am("midday")
    _morning   = ' '.join( (_c_on("in the"), _c_am("morning")) )
    _early     = ' '.join( (_c_on("in the early"), _c_am("morning")) )

    # Peta bagian hari ke teks mereka; lihat pembaruan () di bawah.
    ampm_strings = [
        (1439, _midnight),
        (1260, _night),
        ( 990, _evening),
        ( 722, _afternoon),
        ( 719, _midday),
        ( 360, _morning),
        ( 180, _early),
        (   2, _night),
        (  -1, _midnight)
    ]

    def update(self, h, m):
        """
        Perbarui tampilan jam kata dengan jam dan menit yang ditentukan
        nilai-nilai.
        """
        hour = h % 12
        hour_ = hour + 1
        if hour==0:
            hour = 12

        minute = min(59, m)
        minute_ = (60 - m) % 60

        # Kami hanya akan menyediakan semua ini dan biarkan .format () abaikan
        #  yang tidak perlu, untuk menjaga logika tetap sederhana.
        values = {
            'H': num_strings[hour][0],
            'H_': num_strings[hour_][0],
            'h': num_strings[hour][1],
            'h_': num_strings[hour_][1],
            'M': num_strings[minute][0],
            'M_': num_strings[minute_][0],
            'HH': hour,
            'HH_': hour_,
            'MM': minute,
            'MM_': minute_
        }

        # Loop sampai kami menemukan jangka waktu yang tepat.
        mins = h*60 + m
        for start, text in self.ampm_strings:
            if mins >= start:
                ampm = text
                break

        # Dan kemudian lakukan perakitan akhir teks.
        small = math.ceil(self.font_size * 0.67)
        alt_text = self.alt_time_strings[minute].format(**values).strip()
        if alt_text:
            alt_text = ''.join(( _c_on("("), alt_text, _c_on(")") ))

        self.text = ''.join((
            self.time_strings[minute].format(**values),
            '\n', ampm,
            '\n[size={0}]'.format(small), alt_text, '[/size]'
        ))

############################################################################

class DateDisplay(Label):
    """
    Menampilkan tanggal saat ini dalam bentuk panjang dan dd / mm / yy.
    """
    fmt = ''.join((
        _c_D('%A'), ' ', _c_d('%e'), ' ',
        _c_m('%B'), _c_on(','), ' ',
        _c_y('%Y'), '\n[size={0}]',
        _c_d('%d'), _c_on(config['date_separator']),
        _c_m('%m'), _c_on(config['date_separator']),
        _c_y('%y'), '[/size]'
    ))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.today = None

    def update(self, y, m, d, force=False):
        """
        Perbarui tampilan tanggal ke y / m / d yang ditentukan. Untuk menghindari keberadaan
        tidak efisien pembaruan dilewati jika tanggal tidak berubah
        sejak panggilan terakhir. Argumen `force` ada untuk menggantikan
        ini jika perhitungan ulang diperlukan.
        """
        today = (y, m, d)
        if force or self.today != today:
            small = math.ceil(self.font_size * 0.75)
            self.text = date(*today).strftime(self.fmt.format(small))
            self.today = today

    def on_size(self, *args, **kwargs):
        if self.today is not None:
            self.update(*self.today, force=True)

############################################################################

class BKClock(BoxLayout):
    clock_face = ObjectProperty(None)
    digital_12 = ObjectProperty(None)
    digital_24 = ObjectProperty(None)
    word_clock = ObjectProperty(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.clock_face.start()
        Clock.schedule_interval(self.update, 1/30)

    def update(self, *args):
        """
        Callback tunggal untuk mendapatkan waktu saat ini dan memasukkannya ke jam
        menampilkan.
        """
        now = datetime.now()
        Y, M, D = now.year, now.month, now.day
        h, m, s = now.hour, now.minute, now.second
        u = now.microsecond

        # Perbarui tampilan individual.
        self.clock_face.update(h, m, s, u)
        self.digital_12.update(h, m, s)
        self.digital_24.update(h, m, s)
        self.word_clock.update(h, m)
        self.date_display.update(Y, M, D)

        return True

class BKClockApp(App):
    def build(self):
        return BKClock()

if __name__ == '__main__':
    BKClockApp().run()
