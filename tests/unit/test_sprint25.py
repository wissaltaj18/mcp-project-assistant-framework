"""
Tests Sprint 25 :
- templates détecté comme couche dans MOTIFS_DOSSIERS_COURANTS
- _detecter_correspondances_controller_template() depuis render()
- Rendu enrichi dans FunctionalOverviewReport
"""

from services.functional_overview_analyzer_service import FunctionalOverviewAnalyzerService
from core.entities.functional_overview_report import FunctionalOverviewReport


def _ecrire(tmp_path, chemin, contenu):
    p = tmp_path / chemin
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(contenu, encoding="utf-8")
    return p


# ── Détection couche templates ────────────────────────────────────────────────

class TestDetectionCoucheTemplates:

    def test_detecte_dossier_templates_a_la_racine(self, tmp_path):
        (tmp_path / "templates").mkdir()
        (tmp_path / "templates" / "base.html.twig").write_text("{% block content %}")

        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        fragment = rapport.to_markdown_fragment()

        assert "templates" in fragment

    def test_detecte_dossier_template_singulier(self, tmp_path):
        (tmp_path / "template").mkdir()

        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        fragment = rapport.to_markdown_fragment()

        assert "template" in fragment


# ── Correspondance Controller → Template ─────────────────────────────────────

class TestCorrespondanceControllerTemplate:

    def test_detecte_render_simple(self, tmp_path):
        _ecrire(tmp_path, "src/Controller/HomeController.php",
            "<?php\nclass HomeController {\n"
            "    public function index() {\n"
            "        return $this->render('home/index.html.twig', []);\n"
            "    }\n}"
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert "HomeController" in rapport.controller_template_map
        assert "home/index.html.twig" in rapport.controller_template_map["HomeController"]

    def test_detecte_render_guillemets_doubles(self, tmp_path):
        _ecrire(tmp_path, "src/Controller/CartController.php",
            '<?php\nclass CartController {\n'
            '    public function index() {\n'
            '        return $this->render("cart/index.html.twig", []);\n'
            '    }\n}'
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert "CartController" in rapport.controller_template_map
        assert "cart/index.html.twig" in rapport.controller_template_map["CartController"]

    def test_detecte_plusieurs_renders_dans_meme_controller(self, tmp_path):
        _ecrire(tmp_path, "src/Controller/ProductController.php",
            "<?php\nclass ProductController {\n"
            "    public function index() {\n"
            "        return $this->render('product/index.html.twig', []);\n"
            "    }\n"
            "    public function show() {\n"
            "        return $this->render('product/show.html.twig', []);\n"
            "    }\n}"
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert len(rapport.controller_template_map["ProductController"]) == 2
        assert "product/index.html.twig" in rapport.controller_template_map["ProductController"]
        assert "product/show.html.twig" in rapport.controller_template_map["ProductController"]

    def test_deduplique_meme_template_plusieurs_fois(self, tmp_path):
        _ecrire(tmp_path, "src/Controller/CartController.php",
            "<?php\nclass CartController {\n"
            "    public function a() { return $this->render('cart/index.html.twig'); }\n"
            "    public function b() { return $this->render('cart/index.html.twig'); }\n"
            "}"
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert rapport.controller_template_map["CartController"].count("cart/index.html.twig") == 1

    def test_ignore_les_fichiers_hors_controller(self, tmp_path):
        _ecrire(tmp_path, "src/Service/CartService.php",
            "<?php\nclass CartService {\n"
            "    public function render() {\n"
            "        return $this->render('cart/index.html.twig');\n"
            "    }\n}"
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert rapport.controller_template_map == {}

    def test_pas_de_render_retourne_dict_vide(self, tmp_path):
        _ecrire(tmp_path, "src/Controller/ApiController.php",
            "<?php\nclass ApiController {\n"
            "    public function index() { return new JsonResponse([]); }\n"
            "}"
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        assert "ApiController" not in rapport.controller_template_map

    def test_retrocompatibilite_champ_vide_par_defaut(self):
        rapport = FunctionalOverviewReport()
        assert rapport.controller_template_map == {}
        fragment = rapport.to_markdown_fragment()
        assert "CORRESPONDANCE" not in fragment

    def test_section_correspondance_dans_fragment(self, tmp_path):
        _ecrire(tmp_path, "src/Controller/HomeController.php",
            "<?php\nclass HomeController {\n"
            "    public function index() {\n"
            "        return $this->render('home/index.html.twig', []);\n"
            "    }\n}"
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        fragment = rapport.to_markdown_fragment()
        assert "CORRESPONDANCE CONTROLLER" in fragment
        assert "HomeController" in fragment
        assert "home/index.html.twig" in fragment

    def test_constraint_presente_dans_section(self, tmp_path):
        _ecrire(tmp_path, "src/Controller/HomeController.php",
            "<?php\nclass HomeController {\n"
            "    public function index() {\n"
            "        return $this->render('home/index.html.twig', []);\n"
            "    }\n}"
        )
        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        fragment = rapport.to_markdown_fragment()
        assert "CONSTRAINT" in fragment
        assert "arborescence" in fragment

    def test_scenario_symfony_e_commerce(self, tmp_path):
        for entite in ["Cart", "Product", "User"]:
            _ecrire(tmp_path, f"src/Entity/{entite}.php",
                f"<?php class {entite} {{}}")

        _ecrire(tmp_path, "src/Controller/HomeController.php",
            "<?php\nclass HomeController {\n"
            "    public function index() {\n"
            "        return $this->render('home/index.html.twig', ['products' => $products]);\n"
            "    }\n}"
        )
        _ecrire(tmp_path, "src/Controller/CartController.php",
            "<?php\nclass CartController {\n"
            "    public function index() {\n"
            "        return $this->render('cart/index.html.twig', ['cart' => $cart]);\n"
            "    }\n"
            "    public function show() {\n"
            "        return $this->render('cart/show.html.twig', ['cart' => $cart]);\n"
            "    }\n}"
        )
        (tmp_path / "templates").mkdir()
        (tmp_path / "templates" / "base.html.twig").write_text("{% block content %}")

        rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))
        fragment = rapport.to_markdown_fragment()

        assert "HomeController" in rapport.controller_template_map
        assert "CartController" in rapport.controller_template_map
        assert "home/index.html.twig" in rapport.controller_template_map["HomeController"]
        assert len(rapport.controller_template_map["CartController"]) == 2
        assert "CORRESPONDANCE CONTROLLER" in fragment
        assert "templates" in fragment