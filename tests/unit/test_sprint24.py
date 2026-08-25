"""
Tests Sprint 24 :
- _detecter_relations_doctrine() : attributs PHP8 + annotations Doctrine
- _grouper_routes_par_domaine() : priorité Controller > chemin > Autres
- Rendu enrichi dans FunctionalOverviewReport
"""

from services.functional_overview_analyzer_service import FunctionalOverviewAnalyzerService
from core.entities.functional_overview_report import FunctionalOverviewReport


def _ecrire(tmp_path, chemin, contenu):
    p = tmp_path / chemin
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(contenu, encoding="utf-8")
    return p


# ── Relations Doctrine ────────────────────────────────────────────────────────

class TestRelationsDoctrine:

    def test_detecte_onetomany_format_attribut(self, tmp_path):
        _ecrire(tmp_path, "src/Entity/Cart.php",
            '<?php\nclass Cart {\n'
            '    #[ORM\\OneToMany(targetEntity: CartItem::class, mappedBy: "cart")]\n'
            '    private $items;\n}'
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert "Cart" in rapport.entity_relations
        assert any("OneToMany" in r for r in rapport.entity_relations["Cart"])
        assert any("CartItem" in r for r in rapport.entity_relations["Cart"])

    def test_detecte_manytoone_format_attribut(self, tmp_path):
        _ecrire(tmp_path, "src/Entity/CartItem.php",
            '<?php\nclass CartItem {\n'
            '    #[ORM\\ManyToOne(targetEntity: Cart::class, inversedBy: "items")]\n'
            '    private $cart;\n}'
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert "CartItem" in rapport.entity_relations
        assert any("ManyToOne" in r for r in rapport.entity_relations["CartItem"])
        assert any("Cart" in r for r in rapport.entity_relations["CartItem"])

    def test_detecte_format_annotation_doctrine(self, tmp_path):
        _ecrire(tmp_path, "src/Entity/Product.php",
            '<?php\n/**\n'
            ' * @ORM\\ManyToOne(targetEntity="Category", inversedBy="products")\n'
            ' */\nclass Product {}'
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert "Product" in rapport.entity_relations
        assert any("ManyToOne" in r for r in rapport.entity_relations["Product"])

    def test_detecte_plusieurs_relations_dans_meme_entite(self, tmp_path):
        _ecrire(tmp_path, "src/Entity/CartItem.php",
            '<?php\nclass CartItem {\n'
            '    #[ORM\\ManyToOne(targetEntity: Cart::class, inversedBy: "items")]\n'
            '    private $cart;\n'
            '    #[ORM\\ManyToOne(targetEntity: Product::class)]\n'
            '    private $product;\n}'
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert len(rapport.entity_relations["CartItem"]) == 2

    def test_entite_sans_relation_absente_du_dict(self, tmp_path):
        _ecrire(tmp_path, "src/Entity/User.php",
            '<?php\nclass User {\n    private string $email;\n}'
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert "User" not in rapport.entity_relations

    def test_ignore_les_fichiers_hors_entity(self, tmp_path):
        _ecrire(tmp_path, "src/Service/CartService.php",
            '<?php\n// uses ORM\\OneToMany internally\nclass CartService {}'
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert rapport.entity_relations == {}

    def test_retrocompatibilite_champ_vide_par_defaut(self):
        rapport = FunctionalOverviewReport()
        assert rapport.entity_relations == {}
        fragment = rapport.to_markdown_fragment()
        assert "RELATIONS" not in fragment

    def test_relations_apparaissent_dans_fragment(self, tmp_path):
        _ecrire(tmp_path, "src/Entity/Cart.php",
            '<?php\nclass Cart {\n'
            '    #[ORM\\OneToMany(targetEntity: CartItem::class, mappedBy: "cart")]\n'
            '    private $items;\n}'
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        fragment = rapport.to_markdown_fragment()
        assert "RELATIONS" in fragment
        assert "OneToMany" in fragment
        assert "CartItem" in fragment


# ── Routes par domaine ────────────────────────────────────────────────────────

class TestRouteParDomaine:

    def test_priorite_1_nom_controller(self, tmp_path):
        _ecrire(tmp_path, "src/Entity/Cart.php", "<?php class Cart {}")
        _ecrire(tmp_path, "src/Controller/CartController.php",
            "<?php\nclass CartController {\n"
            "    #[Route('/panier', name: 'cart_index')]\n"
            "    public function index() {}\n}"
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert "Cart" in rapport.routes_par_domaine
        assert "/panier" in rapport.routes_par_domaine["Cart"]

    def test_priorite_2_prefixe_chemin(self, tmp_path):
        _ecrire(tmp_path, "src/Entity/Cart.php", "<?php class Cart {}")
        _ecrire(tmp_path, "src/Controller/ShopController.php",
            "<?php\nclass ShopController {\n"
            "    #[Route('/cart', name: 'cart_view')]\n"
            "    public function view() {}\n}"
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert "Cart" in rapport.routes_par_domaine

    def test_priorite_3_autres_si_aucune_correspondance(self, tmp_path):
        _ecrire(tmp_path, "src/Entity/Cart.php", "<?php class Cart {}")
        _ecrire(tmp_path, "src/Controller/MainController.php",
            "<?php\nclass MainController {\n"
            "    #[Route('/dashboard', name: 'dashboard')]\n"
            "    public function index() {}\n}"
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert "Autres" in rapport.routes_par_domaine
        assert "/dashboard" in rapport.routes_par_domaine["Autres"]

    def test_plusieurs_routes_dans_meme_controller(self, tmp_path):
        _ecrire(tmp_path, "src/Entity/Cart.php", "<?php class Cart {}")
        _ecrire(tmp_path, "src/Controller/CartController.php",
            "<?php\nclass CartController {\n"
            "    #[Route('/cart', name: 'cart_index')]\n"
            "    public function index() {}\n"
            "    #[Route('/cart/{id}', name: 'cart_show')]\n"
            "    public function show() {}\n"
            "    #[Route('/cart/new', name: 'cart_new')]\n"
            "    public function new() {}\n}"
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert len(rapport.routes_par_domaine["Cart"]) == 3

    def test_pas_de_doublon_de_route(self, tmp_path):
        _ecrire(tmp_path, "src/Entity/Cart.php", "<?php class Cart {}")
        _ecrire(tmp_path, "src/Controller/CartController.php",
            "<?php\nclass CartController {\n"
            "    #[Route('/cart', name: 'cart_1')]\n"
            "    #[Route('/cart', name: 'cart_2')]\n"
            "    public function index() {}\n}"
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert rapport.routes_par_domaine.get("Cart", []).count("/cart") == 1

    def test_pas_de_controller_retourne_dict_vide(self, tmp_path):
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert rapport.routes_par_domaine == {}

    def test_retrocompatibilite_champ_vide_par_defaut(self):
        rapport = FunctionalOverviewReport()
        assert rapport.routes_par_domaine == {}

    def test_routes_par_domaine_dans_fragment(self, tmp_path):
        _ecrire(tmp_path, "src/Entity/Cart.php", "<?php class Cart {}")
        _ecrire(tmp_path, "src/Controller/CartController.php",
            "<?php\nclass CartController {\n"
            "    #[Route('/cart', name: 'cart_index')]\n"
            "    public function index() {}\n}"
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        fragment = rapport.to_markdown_fragment()
        assert "ROUTES PAR DOMAINE" in fragment
        assert "Cart" in fragment
        assert "/cart" in fragment

    def test_scenario_e_commerce_complet(self, tmp_path):
        for entite in ["Cart", "Product", "User"]:
            _ecrire(tmp_path, f"src/Entity/{entite}.php",
                f"<?php class {entite} {{}}")
        _ecrire(tmp_path, "src/Controller/CartController.php",
            "<?php\nclass CartController {\n"
            "    #[Route('/cart', name: 'cart_index')]\n"
            "    public function index() {}\n"
            "    #[Route('/cart/{id}', name: 'cart_show')]\n"
            "    public function show() {}\n}"
        )
        _ecrire(tmp_path, "src/Controller/ProductController.php",
            "<?php\nclass ProductController {\n"
            "    #[Route('/product', name: 'product_list')]\n"
            "    public function list() {}\n}"
        )

        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))

        assert "Cart" in rapport.routes_par_domaine
        assert "Product" in rapport.routes_par_domaine
        assert len(rapport.routes_par_domaine["Cart"]) == 2
        assert len(rapport.routes_par_domaine["Product"]) == 1

        fragment = rapport.to_markdown_fragment()
        assert "ROUTES PAR DOMAINE" in fragment
        assert "Cart" in fragment
        assert "Product" in fragment