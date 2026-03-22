"""
MLB Player Position Mapping
-----------------------------
Maps MLBAMID -> ESPN-style position eligibility.
Based on 2024-2025 roster data and positional eligibility.

Position format: primary position(s) separated by /
  e.g. "SS", "OF", "1B/3B", "C/DH"

For ESPN eligibility, a player typically qualifies at a position
if they started 10+ games there in the prior season or 20+ career.
"""

# MLBAMID -> position eligibility string
POSITION_MAP = {
    # ===== CATCHERS =====
    663728: "C",  # Cal Raleigh
    668939: "C",  # Adley Rutschman
    661388: "C",  # William Contreras
    521692: "C/DH",  # Salvador Perez
    669127: "C",  # Shea Langeliers
    673237: "C/DH",  # Yainer Diaz
    671056: "C",  # Iván Herrera
    672386: "C",  # Alejandro Kirk
    669224: "C",  # Austin Wells
    575929: "C/DH",  # Willson Contreras
    680777: "C",  # Ryan Jeffers
    672515: "C",  # Gabriel Moreno
    666310: "C",  # Bo Naylor
    672275: "C",  # Patrick Bailey
    663886: "C",  # Tyler Stephenson
    682626: "C",  # Francisco Alvarez
    681351: "C",  # Logan O'Hoppe
    700337: "C",  # Edgar Quero
    686948: "C",  # Drake Baldwin
    592663: "C",  # J.T. Realmuto
    696100: "C",  # Hunter Goodman
    691016: "C/1B",  # Tyler Soderstrom
    666023: "C",  # Freddy Fermin
    669221: "C",  # Sean Murphy
    605170: "C",  # Victor Caratini
    643376: "C",  # Danny Jansen
    660688: "C",  # Keibert Ruiz
    663743: "C",  # Nick Fortes
    663698: "C",  # Joey Bart
    680779: "C",  # Henry Davis
    657136: "C",  # Connor Wong
    669134: "C",  # Luis Campusano
    624431: "C",  # Jose Trevino
    686780: "C",  # Pedro Pagés
    665804: "C",  # Miguel Amaya
    694208: "C",  # Moisés Ballesteros
    693307: "C",  # Dillon Dingler
    694212: "C",  # Samuel Basallo
    695600: "C",  # Carter Jensen
    691788: "C",  # Joe Mack
    676439: "C",  # Hunter Feduccia
    620443: "C",  # Luis Torrens
    # ===== FIRST BASEMEN =====
    518692: "1B",  # Freddie Freeman
    624413: "1B",  # Pete Alonso
    621566: "1B",  # Matt Olson
    681082: "2B/SS",  # Bryson Stott
    647304: "1B/DH",  # Josh Naylor
    665489: "1B",  # Vladimir Guerrero Jr.
    686469: "1B",  # Vinnie Pasquantino
    694384: "1B",  # Nolan Schanuel
    572233: "1B",  # Christian Walker
    683734: "1B",  # Andrew Vaughn
    605137: "1B/DH",  # Josh Bell
    676475: "1B/OF",  # Alec Burleson
    700250: "1B",  # Ben Rice
    683737: "1B",  # Michael Busch
    701762: "1B",  # Nick Kurtz
    700932: "1B",  # Kyle Manzardo
    656976: "1B",  # Pavin Smith
    502671: "1B",  # Paul Goldschmidt
    656555: "1B/DH",  # Rhys Hoskins
    663993: "1B",  # Nathaniel Lowe
    679529: "1B",  # Spencer Torkelson
    656811: "1B/DH",  # Ryan O'Hearn
    701538: "1B/OF",  # Jackson Merrill
    624585: "1B/DH",  # Jorge Soler
    657757: "1B/OF",  # Gavin Sheets
    # ===== SECOND BASEMEN =====
    543760: "2B",  # Marcus Semien
    650402: "2B",  # Gleyber Torres
    672580: "2B/3B/SS",  # Maikel Garcia
    663538: "2B",  # Nico Hoerner
    645277: "2B",  # Ozzie Albies
    665926: "2B",  # Andrés Giménez
    630105: "2B/1B",  # Jake Cronenworth
    514888: "2B",  # Jose Altuve
    664040: "2B",  # Brandon Lowe
    593871: "2B/3B",  # Jorge Polanco
    671277: "2B",  # Luis García Jr.
    680977: "2B/OF",  # Brendan Donovan
    669242: "2B/SS/OF",  # Tommy Edman
    668930: "2B/SS",  # Brice Turang
    702332: "2B",  # Caleb Durbin
    681393: "2B/OF",  # Connor Norby
    666397: "2B",  # Edouard Julien
    686681: "2B",  # Michael Massey
    663697: "2B/3B",  # Jonathan India
    672761: "2B/OF",  # Wenceel Pérez
    666158: "2B/SS",  # Gavin Lux
    693304: "2B",  # Nick Gonzales
    676391: "2B/3B",  # Ernie Clement
    695681: "2B",  # Christian Moore
    # ===== THIRD BASEMEN =====
    608324: "3B",  # Alex Bregman
    646240: "3B",  # Rafael Devers
    663586: "3B",  # Austin Riley
    656305: "3B",  # Matt Chapman
    571448: "3B",  # Nolan Arenado
    608070: "3B/2B",  # José Ramírez
    553993: "3B",  # Eugenio Suárez
    665862: "3B/OF",  # Jazz Chisholm Jr.
    664761: "3B/1B",  # Alec Bohm
    691406: "3B/SS",  # Junior Caminero
    673962: "3B",  # Josh Jung
    669394: "3B/DH",  # Jake Burger
    682622: "3B",  # Noelvi Marte
    668715: "3B/2B/1B",  # Spencer Steer
    683146: "3B",  # Brett Baty
    668901: "3B/1B",  # Mark Vientos
    663647: "3B",  # Ke'Bryan Hayes
    676059: "3B/2B/SS",  # Jordan Westburg
    691023: "3B/OF",  # Jordan Walker
    669357: "3B/2B",  # Nolan Gorman
    670623: "3B/2B",  # Isaac Paredes
    641933: "3B/OF",  # Tyler O'Neill
    666624: "3B/OF",  # Christopher Morel
    805904: "3B",  # Zach Cole
    681460: "3B/2B",  # Brooks Baldwin
    # ===== SHORTSTOPS =====
    677951: "SS",  # Bobby Witt Jr.
    683002: "SS/3B",  # Gunnar Henderson
    642715: "SS",  # Willy Adames
    607208: "SS",  # Trea Turner
    596019: "SS",  # Francisco Lindor
    682928: "SS",  # CJ Abrams
    678662: "SS",  # Ezequiel Tovar
    687263: "SS",  # Zach Neto
    665161: "SS",  # Jeremy Peña
    682829: "SS",  # Elly De La Cruz
    691026: "SS",  # Masyn Winn
    608369: "SS",  # Corey Seager
    666182: "SS",  # Bo Bichette
    665833: "SS",  # Oneil Cruz
    683011: "SS",  # Anthony Volpe
    621043: "SS",  # Carlos Correa
    593428: "SS",  # Xander Bogaerts
    672695: "SS",  # Geraldo Perdomo
    677587: "SS",  # Brayan Rocchio
    695657: "SS",  # Colson Montgomery
    641487: "SS",  # J.P. Crawford
    669364: "SS/2B",  # Xavier Edwards
    691783: "SS",  # Jordan Lawlar
    805779: "SS",  # Jacob Wilson
    686797: "SS/3B",  # Brooks Lee
    700246: "SS",  # Carson Williams
    695734: "SS",  # Daylen Lile
    691781: "SS",  # Brady House
    683083: "SS",  # Nasim Nuñez
    682668: "SS/2B",  # Luisangel Acuña
    672724: "SS",  # Oswald Peraza
    677649: "SS/3B",  # Ezequiel Duran
    686527: "SS/OF",  # Dominic Canzone
    682657: "SS/2B",  # Angel Martínez
    # ===== OUTFIELDERS =====
    660670: "OF",  # Ronald Acuña Jr.
    660271: "OF/DH",  # Shohei Ohtani
    592450: "OF/DH",  # Aaron Judge
    677594: "OF",  # Julio Rodríguez
    607043: "OF",  # Brandon Nimmo
    668227: "OF",  # Randy Arozarena
    664023: "OF",  # Ian Happ
    656941: "OF/DH",  # Kyle Schwarber
    665742: "OF",  # Juan Soto
    543807: "OF/DH",  # George Springer
    667670: "OF/DH",  # Brent Rooker
    668804: "OF",  # Bryan Reynolds
    682998: "OF",  # Corbin Carroll
    606466: "2B/OF",  # Ketel Marte
    547180: "1B/OF/DH",  # Bryce Harper
    694192: "OF",  # Jackson Chourio
    680757: "OF",  # Steven Kwan
    650333: "1B/OF",  # Luis Arraez
    605141: "2B/SS/OF",  # Mookie Betts
    682985: "OF",  # Riley Greene
    665487: "SS/OF",  # Fernando Tatis Jr.
    680776: "OF",  # Jarren Duran
    641355: "1B/OF",  # Cody Bellinger
    663656: "OF",  # Kyle Tucker
    694671: "OF",  # Wyatt Langford
    673548: "OF",  # Seiya Suzuki
    670541: "OF/DH",  # Yordan Alvarez
    606192: "OF",  # Teoscar Hernández
    621439: "OF/DH",  # Byron Buxton
    650490: "1B/3B/DH",  # Yandy Díaz
    621493: "OF",  # Taylor Ward
    592518: "3B/DH",  # Manny Machado
    671739: "OF",  # Michael Harris II
    686668: "OF",  # Brenton Doyle
    671218: "OF",  # Heliot Ramos
    666969: "OF",  # Adolis García
    691718: "OF",  # Pete Crow-Armstrong
    669065: "OF",  # Kyle Stowers
    681624: "OF",  # Andy Pages
    672640: "OF/2B",  # Otto Lopez
    673357: "OF",  # Luis Robert Jr.
    650489: "OF/2B/3B",  # Willi Castro
    668904: "3B/SS/DH",  # Royce Lewis
    669257: "C",  # Will Smith (catcher)
    678246: "OF/1B",  # Miguel Vargas
    592885: "OF/DH",  # Christian Yelich
    686217: "OF",  # Sal Frelick
    808982: "OF",  # Jung Hoo Lee
    663457: "OF",  # Lars Nootbaar
    681297: "OF",  # Colton Cowser
    657656: "OF",  # Ramón Laureano
    666176: "OF",  # Jo Adell
    680718: "OF/3B",  # Addison Barger
    669701: "OF/3B",  # Josh Smith
    666139: "OF",  # Josh Lowe
    677800: "OF",  # Wilyer Abreu
    681481: "OF/DH",  # Kerry Carpenter
    687363: "OF",  # Victor Scott II
    669016: "OF",  # Brandon Marsh
    657041: "OF",  # Lane Thomas
    656775: "OF",  # Cedric Mullins
    670770: "OF",  # TJ Friedl
    670242: "OF",  # Matt Wallner
    676694: "OF",  # Jake Meyers
    666160: "OF",  # Mickey Moniak
    663616: "OF",  # Trevor Larnach
    694497: "OF",  # Evan Carter
    660821: "OF",  # Jesús Sánchez
    686611: "OF",  # Dylan Crews
    695578: "OF",  # James Wood
    701350: "OF",  # Roman Anthony
    643289: "OF/2B",  # Mauricio Dubón
    687597: "OF",  # Jordan Beck
    664056: "OF",  # Harrison Bader
    687462: "1B/OF",  # Spencer Horwitz
    678882: "SS/OF",  # Ceddanne Rafaela
    671732: "1B/OF",  # Lawrence Butler
    690993: "2B/3B",  # Colt Keith
    669003: "OF",  # Garrett Mitchell
    676914: "OF/2B",  # Davis Schneider
    694388: "OF/1B",  # Joey Loperfido
    664983: "OF",  # Jake McCarthy
    670042: "OF/1B",  # Luke Raley
    671289: "2B/SS/OF",  # Tyler Freeman
    686555: "OF/2B",  # Isaac Collins
    678009: "OF",  # Parker Meadows
    666181: "OF",  # Will Benson
    677942: "SS/OF",  # Blaze Alexander
    681715: "OF",  # Heriberto Hernández
    663837: "OF/1B/3B",  # Matt Vierling
    642708: "SS/OF",  # Amed Rosario
    672356: "SS/3B",  # Gabriel Arias
    671655: "OF",  # George Valera
    672016: "OF",  # Denzel Clarke
    687859: "1B/OF",  # Troy Johnston
    680574: "2B/SS",  # Matt McLain
    573262: "OF",  # Mike Yastrzemski
    592206: "OF",  # Nick Castellanos
    592626: "OF/DH",  # Joc Pederson
    660162: "3B/DH",  # Yoán Moncada
    689414: "OF",  # Liam Hicks
    666018: "1B/DH",  # Jonathan Aranda
    663757: "OF",  # Trent Grisham
    673490: "2B/SS",  # Ha-Seong Kim
    802415: "OF",  # Chandler Simpson
    688363: "1B/OF",  # Graham Pauley
    670764: "SS/2B",  # Taylor Walls
    695506: "1B/OF",  # Jac Caglianone
    641857: "3B/2B",  # Ryan McMahon
    571970: "2B/3B",  # Max Muncy
    650859: "2B/SS",  # Luis Rengifo
    519317: "OF/DH",  # Giancarlo Stanton
    702222: "OF",  # Justin Crawford
    672820: "2B/SS",  # Lenyn Sosa
    665966: "C",  # Carlos Narváez
    668709: "OF",  # JJ Bleday
    676356: "OF",  # Jonny DeLuca
    663368: "OF",  # Blake Perkins
    621438: "OF",  # Tyrone Taylor
    624641: "SS/2B/3B",  # Edmundo Sosa
    608385: "OF/DH",  # Jesse Winker
    807713: "3B/2B",  # Matt Shaw
    695336: "2B/SS",  # Thomas Saggese
    645302: "OF",  # Victor Robles
    595879: "SS",  # Javier Báez
    696285: "OF",  # Jacob Young
    665052: "OF",  # Griffin Conine
    641343: "1B/OF",  # Jake Bauers
    676609: "SS/2B",  # José Caballero
    677950: "OF",  # Alek Thomas
    609280: "OF/1B",  # Miguel Andujar
    602104: "3B/2B/SS",  # Ramón Urías
    691777: "2B",  # Max Muncy (not same as 571970)
    665953: "3B/1B",  # Andrés Chaparro
    663853: "2B/3B",  # Romy Gonzalez
    669236: "SS",  # Jeremiah Jackson
    694673: "OF",  # Abimelec Ortiz
    690022: "SS",  # Ryan Ritter
    665019: "1B/2B/3B",  # Kody Clemens
    669326: "OF",  # Bryce Teodosio
    810938: "SS",  # Ben Williamson
    687401: "3B/SS",  # Joey Ortiz
    701358: "OF",  # Cam Smith
    800050: "OF",  # Chase DeLauter
    596115: "SS",  # Trevor Story
    701807: "OF",  # Carson Benge
    806068: "SS",  # Colt Emerson
    664770: "OF",  # Nathan Lukes
    663968: "OF",  # Jake Mangum
    687515: "OF",  # Colby Thomas
    805300: "OF",  # Jakob Marsee
    808959: "1B/DH",  # Munetaka Murakami
    672960: "1B/3B",  # Kazuma Okamoto
    823550: "OF",  # Sung-Mun Song
    805367: "2B",  # Chase Meidroth
    805808: "1B/OF",  # Bryce Eldridge
    807712: "2B/SS",  # Luke Keaschall
    805811: "1B/OF",  # Bryce Eldridge (alt)
    802139: "SS/2B",  # JJ Wetherholt
    804606: "SS/OF",  # Konnor Griffin
    692632: "SS",  # Cody Morissette
    701398: "3B",  # Sal Stewart
    691019: "C",  # Kyle Teel
    702616: "2B/SS",  # Jackson Holliday
    687637: "OF",  # Dylan Beavers
    683357: "OF",  # Owen Caissie
    691785: "SS",  # Marcelo Mayer
    702284: "SS",  # Cole Young
    545361: "OF/DH",  # Mike Trout
    692382: "C",  # Ethan Salas
    608348: "C",  # Carson Kelly
    467793: "1B/DH",  # Carlos Santana
    621020: "SS",  # Dansby Swanson
    662139: "C/OF",  # Daulton Varsho
    643446: "2B/OF",  # Jeff McNeil
    542303: "OF/DH",  # Marcell Ozuna
    669707: "3B",  # Jared Triolo
    643217: "OF",  # Andrew Benintendi
    682663: "C",  # Agustín Ramírez
    664728: "OF",  # Kyle Isbel
    666971: "OF",  # Lourdes Gurriel Jr.
    669720: "OF",  # Austin Hays
    641584: "OF",  # Jake Fraley
    656716: "2B/3B/SS",  # Zach McKinstry
    668885: "SS/OF",  # Austin Martin
}


def get_position(mlbamid: int, name: str = "") -> str:
    """Look up position by MLBAMID, with fallback to UTIL."""
    if mlbamid in POSITION_MAP:
        return POSITION_MAP[mlbamid]
    return "UTIL"


def get_primary_position(pos_string: str) -> str:
    """Extract primary (first listed) position."""
    return pos_string.split("/")[0]


def get_all_eligible_slots(pos_string: str) -> list[str]:
    """
    Given a position eligibility string like '2B/SS/OF',
    return all roster slots this player can fill.
    """
    positions = pos_string.split("/")
    slots = set()
    for pos in positions:
        slots.add(pos)
        # Infield positions can fill IF slot
        if pos in ("1B", "2B", "3B", "SS"):
            slots.add("IF")
        # Everyone can fill UTIL
        slots.add("UTIL")
    # OF covers all OF slots
    if "OF" in slots:
        slots.add("OF")
    return sorted(slots)
