from enum import Enum as PyEnum
from sqlalchemy import String

class School(str, PyEnum):
    ILOILO = "University of Iloilo"
    ARAULLO = "Araullo University"
    UPANG = "University of Pangasinan"
    STJUDE = "Saint Jude College"
    RIZALLAGUNA = "Rizal College of Laguna"
    COC = "Cagayan De Oro College"
