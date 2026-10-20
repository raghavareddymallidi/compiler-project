from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional
from prune.diagnostics import SourceLocation, Diagnostic, DiagnosticSeverity, CompilerDiagnosticError


class TokenType(Enum):
    # Keywords
    IMPORT = "import"
    EXPORT = "export"
    FROM = "from"
    AS = "as"
    CONST = "const"
    LET = "let"
    VAR = "var"
    FUNCTION = "function"
    RETURN = "return"
    IF = "if"
    ELSE = "else"
    TRUE = "true"
    FALSE = "false"
    NULL = "null"

    # Literals
    IDENTIFIER = "<identifier>"
    NUMBER = "<number>"
    STRING = "<string>"

    # Operators
    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    SLASH = "/"
    PERCENT = "%"
    EQUAL = "="
    EQUAL_EQUAL = "=="
    BANG_EQUAL = "!="
    LESS = "<"
    LESS_EQUAL = "<="
    GREATER = ">"
    GREATER_EQUAL = ">="
    AMP_AMP = "&&"
    PIPE_PIPE = "||"
    BANG = "!"

    # Punctuation
    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    LBRACKET = "["
    RBRACKET = "]"
    SEMICOLON = ";"
    COMMA = ","
    DOT = "."

    # End of File
    EOF = "<eof>"


KEYWORDS = {
    "import": TokenType.IMPORT,
    "export": TokenType.EXPORT,
    "from": TokenType.FROM,
    "as": TokenType.AS,
    "const": TokenType.CONST,
    "let": TokenType.LET,
    "var": TokenType.VAR,
    "function": TokenType.FUNCTION,
    "return": TokenType.RETURN,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "null": TokenType.NULL,
}


@dataclass
class Token:
    type: TokenType
    value: str
    location: SourceLocation

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.location.line}:{self.location.column})"


class Lexer:
    """Handwritten lexer for the Prune module language."""

    def __init__(self, source: str, filename: str = "<stdin>"):
        self.source = source
        self.filename = filename
        self.length = len(source)
        self.offset = 0
        self.line = 1
        self.column = 1

    def _peek(self, offset: int = 0) -> str:
        idx = self.offset + offset
        if idx >= self.length:
            return "\0"
        return self.source[idx]

    def _advance(self) -> str:
        ch = self._peek()
        self.offset += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _make_location(self, start_offset: int, start_line: int, start_col: int) -> SourceLocation:
        return SourceLocation(
            filename=self.filename,
            line=start_line,
            column=start_col,
            start_offset=start_offset,
            end_offset=self.offset,
        )

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while self.offset < self.length:
            ch = self._peek()

            # Skip Whitespace
            if ch in " \t\r\n":
                self._advance()
                continue

            start_offset = self.offset
            start_line = self.line
            start_col = self.column

            # Comments or Slash operator
            if ch == "/":
                next_ch = self._peek(1)
                if next_ch == "/":
                    # Single-line comment
                    self._advance()  # /
                    self._advance()  # /
                    while self.offset < self.length and self._peek() != "\n":
                        self._advance()
                    continue
                elif next_ch == "*":
                    # Multi-line comment
                    self._advance()  # /
                    self._advance()  # *
                    terminated = False
                    while self.offset < self.length:
                        if self._peek() == "*" and self._peek(1) == "/":
                            self._advance()  # *
                            self._advance()  # /
                            terminated = True
                            break
                        self._advance()
                    if not terminated:
                        loc = self._make_location(start_offset, start_line, start_col)
                        raise CompilerDiagnosticError(Diagnostic(
                            message="Unterminated multi-line comment",
                            severity=DiagnosticSeverity.ERROR,
                            location=loc,
                            source_code=self.source,
                            suggestion="Close the comment with '*/'"
                        ))
                    continue

            # Two-character operators
            if ch == "=":
                self._advance()
                if self._peek() == "=":
                    self._advance()
                    tokens.append(Token(TokenType.EQUAL_EQUAL, "==", self._make_location(start_offset, start_line, start_col)))
                else:
                    tokens.append(Token(TokenType.EQUAL, "=", self._make_location(start_offset, start_line, start_col)))
                continue

            if ch == "!":
                self._advance()
                if self._peek() == "=":
                    self._advance()
                    tokens.append(Token(TokenType.BANG_EQUAL, "!=", self._make_location(start_offset, start_line, start_col)))
                else:
                    tokens.append(Token(TokenType.BANG, "!", self._make_location(start_offset, start_line, start_col)))
                continue

            if ch == "<":
                self._advance()
                if self._peek() == "=":
                    self._advance()
                    tokens.append(Token(TokenType.LESS_EQUAL, "<=", self._make_location(start_offset, start_line, start_col)))
                else:
                    tokens.append(Token(TokenType.LESS, "<", self._make_location(start_offset, start_line, start_col)))
                continue

            if ch == ">":
                self._advance()
                if self._peek() == "=":
                    self._advance()
                    tokens.append(Token(TokenType.GREATER_EQUAL, ">=", self._make_location(start_offset, start_line, start_col)))
                else:
                    tokens.append(Token(TokenType.GREATER, ">", self._make_location(start_offset, start_line, start_col)))
                continue

            if ch == "&":
                self._advance()
                if self._peek() == "&":
                    self._advance()
                    tokens.append(Token(TokenType.AMP_AMP, "&&", self._make_location(start_offset, start_line, start_col)))
                    continue
                else:
                    loc = self._make_location(start_offset, start_line, start_col)
                    raise CompilerDiagnosticError(Diagnostic(
                        message=f"Unexpected character '&', did you mean '&&'?",
                        severity=DiagnosticSeverity.ERROR,
                        location=loc,
                        source_code=self.source,
                        suggestion="Use '&&' for logical AND"
                    ))

            if ch == "|":
                self._advance()
                if self._peek() == "|":
                    self._advance()
                    tokens.append(Token(TokenType.PIPE_PIPE, "||", self._make_location(start_offset, start_line, start_col)))
                    continue
                else:
                    loc = self._make_location(start_offset, start_line, start_col)
                    raise CompilerDiagnosticError(Diagnostic(
                        message=f"Unexpected character '|', did you mean '||'?",
                        severity=DiagnosticSeverity.ERROR,
                        location=loc,
                        source_code=self.source,
                        suggestion="Use '||' for logical OR"
                    ))

            # Single-character tokens
            simple_map = {
                "+": TokenType.PLUS,
                "-": TokenType.MINUS,
                "*": TokenType.STAR,
                "/": TokenType.SLASH,
                "%": TokenType.PERCENT,
                "(": TokenType.LPAREN,
                ")": TokenType.RPAREN,
                "{": TokenType.LBRACE,
                "}": TokenType.RBRACE,
                "[": TokenType.LBRACKET,
                "]": TokenType.RBRACKET,
                ";": TokenType.SEMICOLON,
                ",": TokenType.COMMA,
                ".": TokenType.DOT,
            }

            if ch in simple_map:
                val = self._advance()
                tokens.append(Token(simple_map[ch], val, self._make_location(start_offset, start_line, start_col)))
                continue

            # Strings: "..." or '...'
            if ch in ('"', "'"):
                quote = self._advance()
                str_val = []
                terminated = False
                while self.offset < self.length:
                    curr = self._advance()
                    if curr == quote:
                        terminated = True
                        break
                    elif curr == "\\":
                        # escape
                        if self.offset < self.length:
                            escaped = self._advance()
                            if escaped == "n":
                                str_val.append("\n")
                            elif escaped == "t":
                                str_val.append("\t")
                            elif escaped == "r":
                                str_val.append("\r")
                            elif escaped == "\\":
                                str_val.append("\\")
                            elif escaped == quote:
                                str_val.append(quote)
                            else:
                                str_val.append(escaped)
                    elif curr == "\n":
                        loc = self._make_location(start_offset, start_line, start_col)
                        raise CompilerDiagnosticError(Diagnostic(
                            message="Unterminated string literal (newline in string)",
                            severity=DiagnosticSeverity.ERROR,
                            location=loc,
                            source_code=self.source,
                            suggestion=f"Close string literal with {quote} before newline"
                        ))
                    else:
                        str_val.append(curr)

                if not terminated:
                    loc = self._make_location(start_offset, start_line, start_col)
                    raise CompilerDiagnosticError(Diagnostic(
                        message="Unterminated string literal at end of file",
                        severity=DiagnosticSeverity.ERROR,
                        location=loc,
                        source_code=self.source,
                        suggestion=f"Close the string with {quote}"
                    ))

                tokens.append(Token(TokenType.STRING, "".join(str_val), self._make_location(start_offset, start_line, start_col)))
                continue

            # Numbers
            if ch.isdigit():
                num_chars = []
                has_dot = False
                while self.offset < self.length:
                    curr = self._peek()
                    if curr.isdigit():
                        num_chars.append(self._advance())
                    elif curr == "." and not has_dot and self._peek(1).isdigit():
                        has_dot = True
                        num_chars.append(self._advance())
                    else:
                        break
                tokens.append(Token(TokenType.NUMBER, "".join(num_chars), self._make_location(start_offset, start_line, start_col)))
                continue

            # Identifiers and keywords
            if ch.isalpha() or ch in ("_", "$"):
                ident_chars = []
                while self.offset < self.length:
                    curr = self._peek()
                    if curr.isalnum() or curr in ("_", "$"):
                        ident_chars.append(self._advance())
                    else:
                        break
                ident_str = "".join(ident_chars)
                token_type = KEYWORDS.get(ident_str, TokenType.IDENTIFIER)
                tokens.append(Token(token_type, ident_str, self._make_location(start_offset, start_line, start_col)))
                continue

            # Unknown character error
            loc = self._make_location(start_offset, start_line, start_col)
            bad_ch = self._advance()
            raise CompilerDiagnosticError(Diagnostic(
                message=f"Unexpected character: {bad_ch!r}",
                severity=DiagnosticSeverity.ERROR,
                location=loc,
                source_code=self.source,
                suggestion="Remove invalid character"
            ))

        # Add EOF
        eof_loc = SourceLocation(self.filename, self.line, self.column, self.offset, self.offset)
        tokens.append(Token(TokenType.EOF, "", eof_loc))
        return tokens
