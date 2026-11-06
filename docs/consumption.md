# Consommation d'une utilisation

![Ce qu'une utilisation a consommé, le total d'une analyse et celui de l'ensemble](consumption.png)

Chaque utilisation d'une analyse dit ce qu'elle a consommé : l'**électricité**, le **CO₂** que cette électricité a fait
émettre, et l'**eau** qu'elle a coûté, avec à chaque fois de quoi se représenter la quantité.

## Où c'est affiché

- **Résultat d'une utilisation** : sous le résumé de ce qui a été trouvé.
- **Page d'une analyse**, onglet « Utilisations » : le total de toutes ses utilisations mesurées, et une ligne par
  utilisation.
- **Vue d'ensemble** (administrateur) : le total de tout le service.

Une utilisation qui n'a pas été mesurée (celles d'avant cette fonction, ou une mesure qui a échoué) n'affiche rien et ne
compte pour rien dans les totaux.

## D'où viennent les chiffres

| Quoi | Comment |
| --- | --- |
| Électricité (Wh), CO₂ (g), durée | **Mesurés** par le worker avec [CodeCarbon](https://codecarbon.io) autour du calcul d'une utilisation (puissance du processus du worker, intensité carbone du pays). Enregistrés dans la table `runs` (`energy_kwh`, `co2_kg`, `duration_s`). |
| Eau (mL) | **Estimée** par le backend à partir de l'électricité : `WATER_LITERS_PER_KWH` (1,8 L/kWh par défaut, moyenne des centres de données). CodeCarbon ne connaît pas l'eau d'un hôte qui n'est pas celui d'un cloud. |
| Équivalents | **Ordres de grandeur**, tous dans `frontend/src/composables/consumption.ts` : un muffin ≈ 70 Wh de four, une ampoule LED de 10 W, une bouteille de 50 cl, une cuillère à café de 5 mL, une voiture à 200 g de CO₂ par km. |

Les équivalents changent d'échelle avec la quantité : l'électricité se lit en durée d'ampoule LED allumée puis en
muffins cuits, l'eau en cuillères à café puis en bouteilles, le CO₂ en mètres puis en kilomètres de voiture.

## Réglages

Worker :

| Variable | Défaut | Effet |
| --- | --- | --- |
| `MEASURE_CONSUMPTION` | `1` | `0` ne mesure plus rien. |
| `COUNTRY_ISO_CODE` | `FRA` | Le pays dont l'intensité carbone de l'électricité est prise. |
| `CONSUMPTION_TRACKING_MODE` | `process` | `machine` mesure l'hôte entier : trop quand il est partagé. |

Backend : `WATER_LITERS_PER_KWH` (1,8).

## À savoir

- Une mesure ne fait jamais échouer une utilisation : si CodeCarbon ne peut pas lire le matériel, l'utilisation est
  calculée et simplement pas mesurée.
- Seules les utilisations qui se terminent bien sont mesurées : le calcul d'une utilisation en échec ou annulée n'est
  pas compté.
- Dans un conteneur, CodeCarbon ne lit souvent pas la puissance réelle (RAPL) : il l'estime alors à partir du
  processeur. C'est un ordre de grandeur, pas un wattmètre.
- La capture est faite avec des données fictives.
