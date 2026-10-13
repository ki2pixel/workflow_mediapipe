# Masques et Gaussian Blur dans un `.prproj` Premiere 2026 — relevé de format

Ce document décrit les structures qu'écrit Premiere Pro 2026 pour un **masque** et un
**Gaussian Blur**, telles qu'elles ont été relevées sur un projet natif de référence, et
comment `tools/ecproj_to_prproj.py` les reconstruit.

- Source : `W9 - FREQUENSTAR - Mentissa a été victime de racisme_9x16_mask_blur.prproj`
  (masque et blur créés à la main dans Premiere, projet enregistré par l'application puis
  décompressé hors ligne avec `export_filmcraft_encoder/tools/prproj-unpacker/unpack.pl` —
  gzip → XML `PremiereData Version="3"`).
- Le fichier décompressé (7 088 lignes) n'est pas committé (contenu client).

---

## 1. Masque : filtre `AE.ADBE AEMask2`

Un masque est un `<VideoFilterComponent>` (`ClassID d10da199-beea-4dd1-b941-ed3a78766d50`,
`Version 9`) de `MatchName` **`AE.ADBE AEMask2`**, `VideoFilterType 2`, `DisplayName`
`Mask2`, `InstanceName` numérotée (`01` pour le premier masque), **27 paramètres**.

Il est écrit en **sous-composant du filtre Opacité** du clip :

```xml
<VideoFilterComponent>            <!-- Opacité du clip, explicite -->
  <Component Version="7">
    <Params Version="1">…</Params>
    <DisplayName>Opacity</DisplayName><Intrinsic>true</Intrinsic><ID>1</ID>
  </Component>
  <SubComponents Version="1"><SubComponent Index="0" ObjectRef="MASQUE"/></SubComponents>
  <MatchName>AE.ADBE Opacity</MatchName><VideoFilterType>2</VideoFilterType>
</VideoFilterComponent>
```

Conséquence : dès qu'un clip a un masque, l'Opacité devient **explicite** (3 paramètres :
« Opacity » 100, deux « Blend Mode » = 18 et 0) et la chaîne du clip **ne porte plus
`DefaultOpacity`** — ses composants sont alors `[Opacité(+masques), Motion, …]`.

Le track item peut aussi porter `<SelectionComponents>` : c'est l'état d'UI (component
sélectionné dans le panneau Effets), sans effet sur le rendu — ignoré par le writer.

### 1.1 Les 27 paramètres (Index → `ParameterID`)

| Ix | PID | Classe | Nom | Valeur observée (masque réel / masque vide) |
|----|-----|--------|-----|--------------------------------------------|
| 0 | 1 | `cc12343e` | — | `false`, contrôle 11, `UpperBound false` |
| 1 | 2 | `cc12343e` | — | `false`, contrôle 16 |
| 2 | 3 | `cc12343e` | — | `false`, contrôle 16 |
| 3 | 4 | `cc12343e` | — | `false`, contrôle 16 |
| 4 | 19 | `cc12343e` | — | `false`, contrôle 16 |
| 5 | 20 | `cc12343e` | — | `false`, contrôle 16 |
| 6 | 5 | `cc12343e` | — | `false`, contrôle 12, `UpperBound false` |
| 7 | 6 | `313e54d4` (Arb) | Tracker | blob constant |
| 8 | 24 | `313e54d4` | Tracker | blob constant (contient un GUID) |
| 9 | 7 | `313e54d4` | **Path** | **blob du tracé** (§ 1.2) |
| 10 | 8 | `cc12343e` | Transform | `false`, contrôle 11 |
| 11 | 9 | `ca81d347` (Point) | Position | centre de la bbox, normalisé (ex. `0.80603879690170288:0.41775110363960266`) |
| 12 | 11 | `ca81d347` | Scale | `1:1` |
| 13 | 26 | `a4ff2d6e` | Scale Height | `100.` (UI 0-200, bornes ±5000) |
| 14 | 27 | `a4ff2d6e` | Scale Width | `100.` |
| 15 | 28 | `cc12343e` | Uniform Scale | `false` |
| 16 | 12 | `fe47129e` | Rotation | `0.` (contrôle 3, bornes ±32768) |
| 17 | 10 | `ca81d347` | Anchor Point | centre de la bbox (idem Position) |
| 18 | 13 | `cc12343e` | — | `false`, contrôle 12, `UpperBound false` |
| 19 | 14 | `a4ff2d6e` | **Feather** | `0.` (UI ≤ 300, bornes 0-5000) |
| 20 | 15 | `a4ff2d6e` | **Opacity** | `100.` (0-100) |
| 21 | 16 | `a4ff2d6e` | **Expansion** | `0.` (UI ±300, bornes ±5000) |
| 22 | 17 | `cc12343e` | — | `false` |
| 23 | 25 | `a4ff2d6e` | — | `32.` (0-192) |
| 24 | 21 | `6e02e8bb` (enum) | Blend Mode | `0` (0-2, `DiscontinuousInterpolate`) |
| 25 | 22 | `6e02e8bb` | **Type** | `2` = « Add » (0-4, contrôle 10) ; `0` = état par défaut d'Adobe (aucune forme) |
| 26 | 23 | `313e54d4` | User Interactions | `AA==` |

`Type` correspond au **mode** de masque (enum de type AE MaskMode : `2` = Add — mesuré ;
Subtract/Intersect… restent à calibrer). Un masque sans point — celui que Premiere écrit pour
un masque créé mais non dessiné, et le « stub » qu'il garde dans `SelectionComponents` — a un
tracé vide, `Type 0` et `Position/Anchor` à `0:0` : c'est l'état neutre à écrire dans ce cas.

### 1.2 Tracé : blob binaire base64 (paramètre « Path »)

Rectangle 4 sommets = **134 octets** (45 groupes base64) :

```
offset  contenu
0x00    02 00 00 00      32 bits LE = 2   (version du conteneur)
0x04    01 00 00 00      32 bits LE = 1   (nombre de tracés ; 0 = tracé vide)
0x08    56 79 00 00 00   balise « Vy » + remplissage
0x0D    02 00 00 00      constant observée
0x11    04 00 00 00      nombre de sommets (4)
0x15    00 00 00 00      constant observée
0x19    27 floats        float32 LE
0x85    01               1 = tracé fermé, 0 = ouvert (à confirmer sur un tracé ouvert)
```

Les floats : par sommet, **3 points consécutifs** `(tangente d'entrée, sommet, tangente de
sortie)` en coordonnées **absolues normalisées [0..1]** divisées par la taille de la
**source** du clip — l'espace du calque, comme dans After Effects : pour un média paysage
1920×1080 monté dans une séquence 1080×1920, c'est 1920×1080 (le X des masques observés
sort donc de [0..1]) — séparés par un float `0.0` — soit `6N + (N−1)` floats (27 pour N = 4).
Angles vifs : entrée = sortie = sommet (les tangentes `.ecproj`, relatives, sont converties
en absolu).

Un masque **sans sommet** porte le blob `AgAAAAAAAAA=` (= « 2, 0 tracé »).

Décodage de l'échantillon (frame 1080×1920) : `(660.40, 384.38)`, `(1080.65, 384.38)`,
`(1080.65, 1219.78)`, `(660.40, 1219.78)` px — le centre de cette bbox
`(0.80603879690170288, 0.41775110363960266)` est **exactement** le `Position`/`Anchor Point`
du masque (vérifié aussi sur 6 masques réels issus d'EffectCraft).

---

## 1.4 Le `BinaryHash` : une clé, pas une somme de contrôle

Tout élément base64 (`StartKeyframeValue`, `PremiereFilterPrivateData`, `ModificationState`)
porte un attribut `BinaryHash` en forme de GUID. Premiere s'en sert pour **ne stocker qu'une
copie** d'un payload : la première occurrence porte le texte base64, les suivantes sont vides
avec le même hash. Ce champ n'est **ni recalculé ni validé** à la lecture :

- sur les 10 payloads du projet de référence, les 4 derniers octets du hash valent toujours
  « taille du payload + 12 » — et un même payload retombe sur le même hash dans des fichiers
  différents, donc les constantes d'Adobe (données privées du filtre, trackers, interactions,
  tracé vide) ont des hashes **fixes** à réutiliser tels quels ;
- des écrivains tiers en fabriquent librement sans que Premiere s'en plaigne : la
  bibliothèque `py_premiere` (contrat de fidélité octet, validée dans Premiere) écrit
  `BinaryHash=str(uuid.uuid4())` sur ses propres payloads (`Source Text`, `ModificationState`) ;
- un payload **sans** `BinaryHash` est en revanche **ignoré** par Premiere à l'ouverture :
  constaté sur le premier export de l'outil — le masque est ré-enregistré avec un tracé vide
  et le rendu vire au noir.

Conséquence pour l'outil : les payloads constants repris d'Adobe gardent leurs hashes
d'origine ; les tracés calculés reçoivent un hash déterministe dérivé du contenu, à la même
forme (identifiant + taille du blob + 12).

---

## 2. Gaussian Blur : filtre `AE.Impact_Blur_FX`

Le « Gaussian Blur » de Premiere est un `<VideoFilterComponent>` de `MatchName`
**`AE.Impact_Blur_FX`** (`DisplayName` `Gaussian Blur`, `ID 3`), composant **de premier
niveau** de la chaîne (comme Motion), suivi de `DefaultOpacity` — **18 paramètres** :

| Ix | PID | Classe | Nom | Valeur observée |
|----|-----|--------|-----|-----------------|
| 0 | 8100 | `cc12343e` | Error occurred | `false` (contrôle 16) |
| 1 | 1 | `cc12343e` | Controls | `false` (contrôle 11, `UpperBound false`) |
| 2 | 8040 | `cc12343e` | — | `false` (contrôle 16) |
| 3 | 8041 | `a4ff2d6e` | Seed | `0.` (0-99999) |
| 4 | 2 | `fe47129e` | Angle | `0.` (contrôle 3, ±32768) |
| 5 | 3 | `a4ff2d6e` | **Amount** | `20.` (0-100, `CurrentValue` renseignée) |
| 6 | 4 | `a4ff2d6e` | Thickness | `20.` (0-100) |
| 7 | 5 | `cc12343e` | Uniform Blur | `true` |
| 8 | 6 | `a4ff2d6e` | Chromatic Aberration | `0.` (0-100) |
| 9 | 8 | `6e02e8bb` | Edge Behavior | `1` (0-2) |
| 10 | 8240 | `cc12343e` | — | `false` (contrôle 16) |
| 11 | 7 | `cc12343e` | Controls | `false` (contrôle 12, `UpperBound false`) |
| 12 | 8141 | `cc12343e` | — | `false` (contrôle 16) |
| 13 | 8140 | `a4ff2d6e` | Applied Version | `260000.` (0-999999) |
| 14 | 9020 | `cc12343e` | Overlays Enabled | `false` |
| 15 | 9040 | `a4ff2d6e` | Sequence Width | `-1.` |
| 16 | 9041 | `a4ff2d6e` | Sequence Height | `-1.` |
| 17 | 9042 | `a4ff2d6e` | Sequence Pixel Ratio | `-1.` |

Le paramètre « Amount » porte un état d'UI `Node/Properties/ECP.Slider.Expanded` : non écrit
par le convertisseur (cosmétique).

---

## 3. Ce qu'en fait `tools/ecproj_to_prproj.py`

- Masques `.ecproj` **`mode: "Add"`, `inverted: false`** → filtre `AE.ADBE AEMask2` sous
  l'Opacité du clip (matérialisée), tracé via `encode_mask_path()` (§ 1.2) — normalisé par la
  **taille source** du média —, `Position`/`Anchor` = centre de la bbox, `Feather` = plus grand
  des deux axes du `Vec2` d'EffectCraft, `Opacity`/`Expansion` repris, tracé animé limité à sa
  **première clé** (comme l'export `.aep`, avec avertissement) ; un masque **sans point** prend
  l'état par défaut d'Adobe (`Type 0`, `0:0`, tracé vide) ;
- effet **`ec.blur.gaussian`** → filtre `AE.Impact_Blur_FX` (`blurriness` → « Amount », borné
  0-100, « Thickness » aligné sur Amount ; `dimensions`/`repeatEdge` sans équivalent →
  avertissement) ;
- un masque qu'EffectCraft n'applique pas — mode « None », tracé **ouvert** (non fermé), ou
  interrupteur de masque éteint — n'est **pas écrit** : le moteur ne fait aucune transparence
  tant que le tracé n'est pas fermé (`crates/render/src/masks.rs`, règle vérifiée identique dans
  les sources 0.9.2), le calque doit rester entier dans Premiere (les `.ecproj` contiennent
  couramment des masques vides non fermés) ;
- tout le reste (autre mode de masque, inversion, roto-bezier, feather non lisse, feather
  variable par points, motion blur, autre effet) **bloque l'export `.prproj`** (seul le `.aep`
  est produit, un `.prproj` obsolète est supprimé ; `--force` passe outre).

Écarts assumés avec le fichier Adobe : l'état d'UI `ECP.Slider.Expanded` est omis, et chaque
occurrence d'un payload porte son texte (avec le même `BinaryHash`) là où Adobe n'écrit le
texte qu'une fois — Premiere résout les deux formes (§ 1.4).

### À calibrer (échantillon complémentaire recommandé)

Un second projet natif contenant : un masque `Feather = 50`, un masque `Subtract`, un masque
inversé, un tracé **animé**, un tracé **ouvert**, un **contour à plus de 255 sommets** et un
Gaussian Blur `Amount = 50` — permet de confirmer : l'unité du feather, le paramètre
d'inversion, les valeurs d'énumération `Type` pour Subtract/Intersect, l'encodage des
keyframes d'un paramètre de masque, le drapeau « ouvert » et l'ordre des octets du nombre de
sommets au-delà de 255 (les variantes d'encodage coïncident en dessous de 256, ce qui couvre
tous les masques observés).
