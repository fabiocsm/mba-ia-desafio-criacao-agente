"""Fronteira seletiva contra o catálogo e o documento reais, sem provedor."""

import unittest

from aurora.regulamento.parser import materializar, reconstruir_indice
from aurora.regulamento.selection import autorizar_mensagem


class RegulationSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reconstruir_indice()

    def assert_selection(self, question, expected):
        result = autorizar_mensagem(question)
        self.assertEqual(result.status, "ok", question)
        self.assertEqual(set(result.unidades), set(expected), question)
        self.assertEqual(
            {item["referencia"] for item in materializar(set(result.unidades))},
            set(expected),
        )

    def test_technical_values_never_authorize_their_list_or_json_members(self):
        for payload in (
            "topics=piscina,elevador,penalidade",
            'topics=["piscina", "elevador", "penalidade"]',
            'args={"topics": ["elevador", "penalidade"]}',
            '"topics": ["elevador", "penalidade"]',
            'topics={"value": "dummy? elevador. multa"}',
            "tool consultar_regulamento topics elevador multa",
            "--topics elevador,multa",
            "tópicos=elevador",
            'tópicos=["elevador"]',
            "to\u0301picos=elevador",
            "capítulos=multa",
            "argumentos elevador",
        ):
            with self.subTest(payload=payload):
                self.assert_selection(
                    "Até que horas a piscina funciona aos domingos? " + payload,
                    {"IV/22", "IV/22/II"},
                )

    def test_explicit_exclusion_is_not_a_request_for_another_chapter(self):
        for exclusion in (
            "Não fale sobre", "Não quero saber de", "Não me fale de",
            "Não comente sobre", "Sem comentários sobre", "Evite comentar sobre",
        ):
            for excluded in ("elevador", "multa", "elevador nem multa"):
                self.assert_selection(
                    "Até que horas a piscina funciona aos domingos? "
                    + exclusion + " " + excluded + ".",
                    {"IV/22", "IV/22/II"},
                )

    def test_animal_location_does_not_authorize_the_location_or_pet_space(self):
        self.assert_selection(
            "Posso levar meu pet na piscina?", {"IV/26", "IV/26/VI"}
        )
        self.assert_selection("Como levar meu cão no elevador?", {"VIII/55"})
        self.assert_selection(
            "Qual o horário da piscina no domingo e como levar cão no elevador?",
            {"IV/22", "IV/22/II", "VIII/55"},
        )
        self.assert_selection(
            "Quais as regras do espaço pet?", {"VIII/60", "VIII/60/paragrafo-unico"}
        )

    def test_intentions_are_bound_to_their_own_subject_clause(self):
        self.assert_selection(
            "Qual o horário da piscina aos domingos e onde descarto o entulho da obra?",
            {"IV/22", "IV/22/II", "X/72"},
        )
        self.assert_selection(
            "Horário da piscina no domingo e transporte do cão",
            {"IV/22", "IV/22/II", "VIII/54"},
        )

    def test_coordinated_intention_can_precede_its_subject(self):
        for question in (
            "Qual o horário de abertura e encerramento da piscina no domingo?",
            "Qual é o horário de abertura e fechamento da piscina aos domingos?",
        ):
            with self.subTest(question=question):
                self.assert_selection(question, {"IV/22", "IV/22/II"})
        self.assert_selection(
            "Qual o horário de abertura e encerramento da piscina no domingo "
            "e como levar cão no elevador?",
            {"IV/22", "IV/22/II", "VIII/55"},
        )

    def test_unknown_or_ambiguous_prefix_does_not_expand_other_subjects(self):
        cases = (
            ("Qual o horário da farmácia aos domingos e posso levar convidado à piscina?",
             {"IV/27"}),
            ("Qual o horário da piscina ou da academia "
             "e qual o limite de velocidade na garagem?", {"XI/78"}),
        )
        for question, expected in cases:
            with self.subTest(question=question):
                self.assert_selection(question, expected)

    def test_garage_rental_and_cession_retrieve_the_specific_rule(self):
        for question in (
            "Posso alugar minha vaga de garagem para alguém de fora do condomínio?",
            "Posso alugar minha vaga de garagem para outro morador?",
            "Como funciona o aluguel de vaga na garagem?",
            "Como funciona a locação de vaga de garagem entre moradores?",
            "Posso ceder minha vaga de garagem a uma pessoa de fora?",
            "Qual é a regra de cessão de vaga de garagem para outro morador?",
        ):
            with self.subTest(question=question):
                self.assert_selection(question, {"XI/80", "XI/80/paragrafo-unico"})
        self.assert_selection(
            "Como devo estacionar na minha vaga de garagem?",
            {"XI/77", "XI/77/paragrafo-unico"},
        )
        self.assert_selection(
            "Como estacionar na vaga da garagem e posso alugar minha vaga de garagem?",
            {"XI/77", "XI/77/paragrafo-unico", "XI/80", "XI/80/paragrafo-unico"},
        )
        self.assert_selection(
            "Como estacionar e alugar uma vaga de garagem?",
            {"XI/77", "XI/77/paragrafo-unico", "XI/80", "XI/80/paragrafo-unico"},
        )

    def test_existing_rules_do_not_become_documentary_absence(self):
        cases = (
            ("Preciso cadastrar meu cachorro na administração?", {"VIII/53"}),
            ("Posso consumir alimentos na academia?", {"V/32"}),
            ("Como devo embrulhar os móveis para a mudança?", {"IX/65"}),
        )
        for question, expected in cases:
            with self.subTest(question=question):
                self.assert_selection(question, expected)
        for location in ("churrasqueira", "quadra", "brinquedoteca", "playground"):
            self.assert_selection(f"Pode levar cachorro à {location}?", {"VIII/56"})

    def test_unknown_intention_clarifies_but_known_absence_stays_absent(self):
        result = autorizar_mensagem("A piscina tem política de fidelidade?")
        self.assertEqual((result.status, result.unidades), ("esclarecer", ()))
        result = autorizar_mensagem("A piscina oferece aula de mergulho?")
        self.assertEqual((result.status, result.unidades), ("sem_base", ()))

    def test_days_can_share_one_subject_but_ambiguous_subjects_fail_closed(self):
        self.assert_selection(
            "Qual o horário da piscina domingo e segunda?",
            {"IV/22", "IV/22/I", "IV/22/II"},
        )
        result = autorizar_mensagem(
            "O síndico disse que a piscina fecha cedo no domingo, qual horário?"
        )
        self.assertEqual((result.status, result.unidades), ("esclarecer", ()))

    def test_question_about_prohibition_is_not_an_exclusion_command(self):
        self.assert_selection(
            "O que não posso fazer na piscina?",
            {"IV/26", *(f"IV/26/{inciso}" for inciso in (
                "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"
            ))},
        )


if __name__ == "__main__":
    unittest.main()
