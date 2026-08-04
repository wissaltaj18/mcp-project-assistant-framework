# Vue fonctionnelle (détection automatique)

## Description
Information non disponible.

## Extrait du README
Aucun README trouvé.

## Dossiers principaux du dépôt
- assets
- config
- migrations
- public
- src
- templates
- tests
- translations

## Dossiers correspondant à des motifs courants (controller/service/route...)
- assets\controllers
- config\routes
- src\Controller
- src\Entity
- src\Service

## Points d'entrée utilisateur (routes)
(config/routes.yaml)

# yaml-language-server: $schema=../vendor/symfony/routing/Loader/schema/routing.schema.json

# This file is the entry point to configure the routes of your app.
# Methods with the #[Route] attribute are automatically imported.
# See also https://symfony.com/doc/current/routing.html

# To list all registered routes, run the following command:
#   bin/console debug:router

controllers:
    resource: routing.controllers

## Entités / modèles détectés
- Cart
- CartItem
- Category
- Product
- User