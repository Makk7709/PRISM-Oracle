# ADR-006 — Contrat d'integrite des entrees/sorties des tools

**Date :** 4 mai 2026
**Statut :** Accepte
**Auteur :** Amine Mohamed

## Contexte

Le 4 mai 2026, l'audit de la session `yENoyKIZ` (compte `amine`, generation d'un dossier d'integration engineering pour Aya) a revele un defaut structurel du tool `file_writer`.

L'agent avait ecrit un markdown de 49 969 octets dans `/app/tmp/korev_dossier_content.md` puis avait appele `file_writer` avec `content="§§include(/app/tmp/korev_dossier_content.md)"`. Le repertoire `tmp/` ne figurant pas dans `ALLOWED_INCLUDE_DIRS` (`tmp/uploads`, `tmp/generated`, `docs`, `work_dir`), la directive d'include n'a pas pu etre resolue. Pourtant `file_writer` a poursuivi sa pipeline et genere un PDF de 25 434 octets dont le corps utile etait la chaine litterale `§§include(/app/tmp/korev_dossier_content.md)`. Le `Response.message` retourne par le tool annoncait `✅ File created successfully!`.

L'utilisateur final a recu un PDF de six lignes alors que le chat indiquait qu'un dossier complet de 742 lignes lui avait ete livre. C'est exactement le motif de defaut identifie en interne sous l'expression *"ecart entre capacite declaree et verrou bloquant effectif"* (cf. `audit-hostile-valorisation/01-executive-summary.md`).

L'incident a expose une lacune contractuelle plus large : les tools de KOREV Evidence ne disposaient pas d'une regle ecrite garantissant que la valeur de retour `Response.message` reflete fidelement l'etat du systeme de fichiers apres execution.

## Decision

Tout tool qui ecrit un artefact sur disque DOIT respecter le contrat d'integrite suivant :

1. **Atomicite des transformations preparatoires** — toute transformation du contenu (resolution d'includes, normalisation de templates, expansion de variables) DOIT s'executer integralement et avec succes AVANT la moindre ouverture en ecriture du fichier de sortie. Si une de ces transformations echoue partiellement, le tool DOIT lever une erreur sans avoir touche au systeme de fichiers.

2. **Fail-loud sur entree corrompue** — si la transformation preparatoire ne peut pas produire un contenu coherent (directive d'include non resolue, variable manquante, fichier reference absent ou non lisible, encodage non UTF-8 sur un input texte), le tool DOIT retourner une `Response` d'erreur explicite. Aucun artefact ne doit etre ecrit, meme partiel.

3. **Message d'erreur exploitable par l'agent** — la `Response.message` d'erreur doit citer verbatim chaque entree fautive, lister les contraintes pertinentes (exemple : `ALLOWED_INCLUDE_DIRS`), proposer au moins une action corrective concrete, et ne contenir ni stack trace Python ni chemin absolu hors des repertoires autorises.

4. **Reflet exact du systeme de fichiers** — un `Response.message` annoncant un succes ne doit etre retourne que si l'artefact a ete ecrit complet, dans le repertoire annonce, avec une taille proportionnee au contenu attendu. Un succes apparent recouvrant un echec interne (fichier vide, fichier de taille fixe independante de l'input, fichier contenant une directive non expandee) est interdit.

5. **Observabilite** — toute erreur de transformation doit produire au minimum un log au niveau `WARNING` (cf. `PrintStyle(font_color="red")`). Les logs ne se substituent pas a la `Response`, ils la completent.

## Consequences

**Positives :**

- Suppression d'un mode de defaillance silencieux qui pouvait livrer un artefact factice a l'utilisateur final tout en marquant la session comme reussie dans `chat.json` et le `replay_snapshot`.
- L'agent recoit desormais une erreur actionable lorsqu'il commet le pattern "ecrire dans un repertoire non autorise puis inclure le fichier" : il peut soit deplacer le fichier dans `tmp/uploads`, soit inliner directement le contenu.
- L'invariant fail-loud est testable et teste : la suite `tests/security/test_file_writer_includes_failure.py` couvre 14 cas et les invariants I-1, I-2, I-4, I-5 du plan de correction sont verifies. La suite `tests/integration/test_file_writer_pdf_integrity.py` verifie l'invariant au niveau du rendu PDF reel (WeasyPrint) avec ratio taille PDF / taille markdown source.
- Le scenario exact de la session `yENoyKIZ` est verrouille dans `tests/regression/test_session_yenoyikz_repro.py` : toute regression de ce comportement fera echouer la CI.

**Negatives :**

- Modification de contrat au niveau du tool. Les sessions actives au moment du deploiement qui dependaient du retour silencieux verront un changement de message agent. Le risque est limite car l'ancien comportement etait un bug : aucune session connue ne s'appuyait dessus volontairement.
- Le snapshot test du message d'erreur (`test_T13_snapshot_format_is_stable`) cassera des qu'on retouchera la chaine de format. La procedure de mise a jour est documentee dans le test : le snapshot doit etre revu en pull request.
- Le contrat ne s'applique pour le moment qu'a `file_writer`. Les autres tools (`pdf_ocr`, `export_strategic_pdf`, `code_execution_tool` quand il ecrit un fichier) doivent etre audites separement et alignes sur le contrat. C'est un travail de suivi, hors perimetre du fix immediat.

## Alternatives rejetees

| Alternative | Raison du rejet |
|---|---|
| **Etendre `ALLOWED_INCLUDE_DIRS` avec `tmp/`** | Resoudrait le symptome `yENoyKIZ` mais laisserait intact le motif "succes apparent recouvrant un echec interne". Un autre cas (encodage casse, fichier vide, template manquant) reproduirait le meme defaut. Le verrou doit etre sur le contrat, pas sur la liste des chemins autorises. |
| **Rendre la directive `§§include(...)` synchrone et obligatoire (rejet de tout `content` qui en contient)** | Casserait le mecanisme de fallback qui a justement ete prevu pour les modeles qui referencent au lieu d'inliner. La solution n'est pas d'interdire la directive mais de garantir sa resolution complete ou son echec atomique. |
| **Ajouter un seuil de taille minimum sur le PDF genere** | Heuristique fragile : le seuil correct depend du contenu. Le contrat doit etre exprime en termes de coherence input/output, pas de taille seuil arbitraire. Les tests d'integration verifient un ratio empirique mais c'est une mesure de defense en profondeur, pas le verrou principal. |
| **Logger l'erreur sans bloquer** | Inadequat : c'est exactement le comportement actuel qui a produit l'incident. Les logs ne sont pas vus par l'agent en temps reel ; seul le `Response.message` modifie son comportement. |

## Implementation de reference

Fichier `python/tools/file_writer.py` :

- Classe `IncludeResolutionError(Exception)` qui transporte la liste des chemins non resolus.
- `_resolve_includes(content)` resout d'abord toutes les directives, puis substitue uniquement si l'integralite de la resolution a reussi. Sinon leve `IncludeResolutionError`. Atomicite all-or-nothing.
- `execute()` enveloppe l'appel a `_resolve_includes` dans un `try/except` qui retourne une `Response` d'erreur formatee par `_format_include_error` avant toute ouverture de fichier de sortie.
- `_format_include_error` produit un message d'erreur exploitable par l'agent, conforme au point 3.
- `_read_include_file` capture egalement `UnicodeDecodeError` afin que les fichiers binaires ou non-UTF-8 declenchent le meme echec atomique (le `UnicodeDecodeError` n'etait pas catche dans la version precedente, ce qui aurait pu provoquer un crash non gere).

## Suivi recommande

- Etendre l'audit a `python/tools/export_strategic_pdf.py`, `python/tools/pdf_ocr.py` et a tout autre tool ecrivant un artefact. Verifier la conformite au present contrat. Ouvrir un ticket par tool si un ecart est detecte.
- Recalibrer dans 60 jours le ratio empirique `taille_pdf / taille_markdown` du test `test_T14_pdf_size_proportional_to_content` sur un corpus elargi de PDFs production (au moins 10 dossiers de reference au lieu de 3).
- Etudier l'opportunite d'ajouter un test d'integrite cryptographique systematique (hash du contenu attendu vs hash du contenu lu apres ecriture) pour les artefacts critiques, compatible avec le `replay_snapshot`.
