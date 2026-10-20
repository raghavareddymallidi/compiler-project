import pytest
from prune.lexer import Lexer, TokenType
from prune.diagnostics import CompilerDiagnosticError


def test_lex_basic_tokens():
    source = 'const x = 42;\nlet y = "hello";\nexport function add(a, b) { return a + b; }'
    lexer = Lexer(source, filename="main.prune")
    tokens = lexer.tokenize()

    types = [t.type for t in tokens]
    expected = [
        TokenType.CONST, TokenType.IDENTIFIER, TokenType.EQUAL, TokenType.NUMBER, TokenType.SEMICOLON,
        TokenType.LET, TokenType.IDENTIFIER, TokenType.EQUAL, TokenType.STRING, TokenType.SEMICOLON,
        TokenType.EXPORT, TokenType.FUNCTION, TokenType.IDENTIFIER, TokenType.LPAREN,
        TokenType.IDENTIFIER, TokenType.COMMA, TokenType.IDENTIFIER, TokenType.RPAREN,
        TokenType.LBRACE, TokenType.RETURN, TokenType.IDENTIFIER, TokenType.PLUS, TokenType.IDENTIFIER,
        TokenType.SEMICOLON, TokenType.RBRACE, TokenType.EOF
    ]
    assert types == expected
    assert tokens[3].value == "42"
    assert tokens[8].value == "hello"


def test_lex_operators_and_comparisons():
    source = "== != <= >= < > && || ! + - * / %"
    tokens = Lexer(source).tokenize()
    types = [t.type for t in tokens[:-1]]
    assert types == [
        TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL, TokenType.LESS_EQUAL, TokenType.GREATER_EQUAL,
        TokenType.LESS, TokenType.GREATER, TokenType.AMP_AMP, TokenType.PIPE_PIPE, TokenType.BANG,
        TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.PERCENT
    ]


def test_lex_comments():
    source = """
    // Single line comment
    const a = 1; /* inline comment */
    /*
     * Multi-line comment
     */
    const b = 2;
    """
    tokens = Lexer(source).tokenize()
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert types == [
        TokenType.CONST, TokenType.IDENTIFIER, TokenType.EQUAL, TokenType.NUMBER, TokenType.SEMICOLON,
        TokenType.CONST, TokenType.IDENTIFIER, TokenType.EQUAL, TokenType.NUMBER, TokenType.SEMICOLON
    ]


def test_lex_source_locations():
    source = "const\n  answer = 42;"
    tokens = Lexer(source, filename="test.prune").tokenize()
    t_const = tokens[0]
    assert t_const.location.line == 1
    assert t_const.location.column == 1

    t_ident = tokens[1]
    assert t_ident.value == "answer"
    assert t_ident.location.line == 2
    assert t_ident.location.column == 3


def test_lex_unterminated_string():
    source = 'const s = "broken;'
    with pytest.raises(CompilerDiagnosticError) as exc_info:
        Lexer(source).tokenize()
    diag = exc_info.value.diagnostic
    assert "Unterminated string" in diag.message


def test_lex_unterminated_comment():
    source = "/* unterminated comment"
    with pytest.raises(CompilerDiagnosticError) as exc_info:
        Lexer(source).tokenize()
    diag = exc_info.value.diagnostic
    assert "Unterminated multi-line comment" in diag.message


def test_lex_unexpected_char():
    source = "const @ = 123;"
    with pytest.raises(CompilerDiagnosticError) as exc_info:
        Lexer(source).tokenize()
    diag = exc_info.value.diagnostic
    assert "Unexpected character" in diag.message
