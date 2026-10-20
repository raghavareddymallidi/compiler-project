from __future__ import annotations
from typing import List, Optional, Set
from prune.lexer import Token, TokenType, Lexer
from prune.ast_nodes import (
    Program, Statement, Expression, ImportDecl, ImportSpecifier,
    ExportDecl, ExportNamedDecl, ExportSpecifier, VarDecl, VariableDeclarator,
    FunctionDecl, IfStmt, ReturnStmt, BlockStmt, ExprStmt,
    AssignmentExpr, BinaryExpr, UnaryExpr, CallExpr,
    Identifier, NumberLiteral, StringLiteral, BooleanLiteral, NullLiteral
)
from prune.diagnostics import SourceLocation, Diagnostic, DiagnosticSeverity, CompilerDiagnosticError


class Parser:
    """Handwritten recursive-descent parser with operator precedence climbing."""

    def __init__(self, tokens: List[Token], source: str = "", filename: str = "<stdin>"):
        self.tokens = tokens
        self.source = source
        self.filename = filename
        self.pos = 0

    @classmethod
    def from_source(cls, source: str, filename: str = "<stdin>") -> Parser:
        lexer = Lexer(source, filename=filename)
        tokens = lexer.tokenize()
        return cls(tokens, source=source, filename=filename)

    def _current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]

    def _peek(self, offset: int = 1) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def _is_at_end(self) -> bool:
        return self._current().type == TokenType.EOF

    def _advance(self) -> Token:
        token = self._current()
        if not self._is_at_end():
            self.pos += 1
        return token

    def _check(self, token_type: TokenType) -> bool:
        if self._is_at_end():
            return token_type == TokenType.EOF
        return self._current().type == token_type

    def _match(self, *token_types: TokenType) -> bool:
        for tt in token_types:
            if self._check(tt):
                self._advance()
                return True
        return False

    def _consume(self, token_type: TokenType, error_message: str, suggestion: Optional[str] = None) -> Token:
        if self._check(token_type):
            return self._advance()
        token = self._current()
        raise CompilerDiagnosticError(Diagnostic(
            message=f"{error_message}, found {token.value!r} ({token.type.value if isinstance(token.type.value, str) else token.type.name})",
            severity=DiagnosticSeverity.ERROR,
            location=token.location,
            source_code=self.source,
            suggestion=suggestion
        ))

    def parse(self) -> Program:
        start_loc = self._current().location
        statements: List[Statement] = []

        while not self._is_at_end():
            # Skip stray semicolons
            if self._match(TokenType.SEMICOLON):
                continue
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)

        end_loc = self._current().location
        prog_loc = SourceLocation(
            self.filename,
            start_loc.line,
            start_loc.column,
            start_loc.start_offset,
            end_loc.end_offset
        )
        return Program(location=prog_loc, body=statements)

    # -------------------------------------------------------------
    # Statement Parsing
    # -------------------------------------------------------------

    def _parse_statement(self) -> Statement:
        curr = self._current()

        if curr.type == TokenType.IMPORT:
            return self._parse_import_declaration()
        elif curr.type == TokenType.EXPORT:
            return self._parse_export_declaration()
        elif curr.type in (TokenType.CONST, TokenType.LET, TokenType.VAR):
            return self._parse_variable_declaration()
        elif curr.type == TokenType.FUNCTION:
            return self._parse_function_declaration()
        elif curr.type == TokenType.IF:
            return self._parse_if_statement()
        elif curr.type == TokenType.RETURN:
            return self._parse_return_statement()
        elif curr.type == TokenType.LBRACE:
            return self._parse_block_statement()
        else:
            return self._parse_expression_statement()

    def _parse_import_declaration(self) -> ImportDecl:
        start_token = self._consume(TokenType.IMPORT, "Expected 'import'")
        self._consume(TokenType.LBRACE, "Expected '{' after 'import'", suggestion="Named imports must be enclosed in curly braces: import { name } from './module'")

        specifiers: List[ImportSpecifier] = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            spec_start = self._current().location
            imported_tok = self._consume(TokenType.IDENTIFIER, "Expected imported symbol name")
            local_name = imported_tok.value

            if self._match(TokenType.AS):
                local_tok = self._consume(TokenType.IDENTIFIER, "Expected identifier after 'as'")
                local_name = local_tok.value

            specifiers.append(ImportSpecifier(
                location=SourceLocation(self.filename, spec_start.line, spec_start.column, spec_start.start_offset, self._current().location.start_offset),
                imported=imported_tok.value,
                local=local_name
            ))

            if not self._match(TokenType.COMMA):
                break

        self._consume(TokenType.RBRACE, "Expected '}' after import specifiers")
        self._consume(TokenType.FROM, "Expected 'from' after import specifiers")

        source_tok = self._consume(TokenType.STRING, "Expected module path string after 'from'")
        end_loc = source_tok.location
        if self._check(TokenType.SEMICOLON):
            end_loc = self._advance().location

        return ImportDecl(
            location=SourceLocation(self.filename, start_token.location.line, start_token.location.column, start_token.location.start_offset, end_loc.end_offset),
            specifiers=specifiers,
            source=source_tok.value
        )

    def _parse_export_declaration(self) -> Statement:
        start_token = self._consume(TokenType.EXPORT, "Expected 'export'")

        # Case 1: export { a, b as c };
        if self._check(TokenType.LBRACE):
            self._advance()
            specifiers: List[ExportSpecifier] = []
            while not self._check(TokenType.RBRACE) and not self._is_at_end():
                spec_start = self._current().location
                local_tok = self._consume(TokenType.IDENTIFIER, "Expected identifier in export specifier")
                exported_name = local_tok.value

                if self._match(TokenType.AS):
                    exported_tok = self._consume(TokenType.IDENTIFIER, "Expected identifier after 'as'")
                    exported_name = exported_tok.value

                specifiers.append(ExportSpecifier(
                    location=SourceLocation(self.filename, spec_start.line, spec_start.column, spec_start.start_offset, self._current().location.start_offset),
                    local=local_tok.value,
                    exported=exported_name
                ))

                if not self._match(TokenType.COMMA):
                    break

            self._consume(TokenType.RBRACE, "Expected '}' after export specifiers")
            end_loc = self._current().location
            if self._check(TokenType.SEMICOLON):
                end_loc = self._advance().location

            return ExportNamedDecl(
                location=SourceLocation(self.filename, start_token.location.line, start_token.location.column, start_token.location.start_offset, end_loc.end_offset),
                specifiers=specifiers
            )

        # Case 2: export const/let/var or export function
        if self._check(TokenType.FUNCTION):
            func_decl = self._parse_function_declaration()
            return ExportDecl(
                location=SourceLocation(self.filename, start_token.location.line, start_token.location.column, start_token.location.start_offset, func_decl.location.end_offset),
                declaration=func_decl
            )
        elif self._current().type in (TokenType.CONST, TokenType.LET, TokenType.VAR):
            var_decl = self._parse_variable_declaration()
            return ExportDecl(
                location=SourceLocation(self.filename, start_token.location.line, start_token.location.column, start_token.location.start_offset, var_decl.location.end_offset),
                declaration=var_decl
            )
        else:
            token = self._current()
            raise CompilerDiagnosticError(Diagnostic(
                message=f"Expected variable or function declaration after 'export', found {token.value!r}",
                severity=DiagnosticSeverity.ERROR,
                location=token.location,
                source_code=self.source,
                suggestion="Use 'export const/let/var', 'export function', or 'export { name }'"
            ))

    def _parse_variable_declaration(self) -> VarDecl:
        kind_tok = self._advance()
        kind = kind_tok.value  # const, let, var

        declarations: List[VariableDeclarator] = []
        while True:
            id_tok = self._consume(TokenType.IDENTIFIER, "Expected variable name")
            init: Optional[Expression] = None

            if self._match(TokenType.EQUAL):
                init = self._parse_expression()
            elif kind == "const":
                raise CompilerDiagnosticError(Diagnostic(
                    message=f"Missing initializer in const declaration '{id_tok.value}'",
                    severity=DiagnosticSeverity.ERROR,
                    location=id_tok.location,
                    source_code=self.source,
                    suggestion="const declarations must be initialized with a value"
                ))

            end_loc = init.location if init else id_tok.location
            declarations.append(VariableDeclarator(
                location=SourceLocation(self.filename, id_tok.location.line, id_tok.location.column, id_tok.location.start_offset, end_loc.end_offset),
                id=id_tok.value,
                init=init
            ))

            if not self._match(TokenType.COMMA):
                break

        end_loc = declarations[-1].location
        if self._check(TokenType.SEMICOLON):
            end_loc = self._advance().location

        return VarDecl(
            location=SourceLocation(self.filename, kind_tok.location.line, kind_tok.location.column, kind_tok.location.start_offset, end_loc.end_offset),
            kind=kind,
            declarations=declarations
        )

    def _parse_function_declaration(self) -> FunctionDecl:
        start_tok = self._consume(TokenType.FUNCTION, "Expected 'function'")
        id_tok = self._consume(TokenType.IDENTIFIER, "Expected function name")
        self._consume(TokenType.LPAREN, "Expected '(' after function name")

        params: List[str] = []
        if not self._check(TokenType.RPAREN):
            while True:
                param_tok = self._consume(TokenType.IDENTIFIER, "Expected parameter name")
                params.append(param_tok.value)
                if not self._match(TokenType.COMMA):
                    break

        self._consume(TokenType.RPAREN, "Expected ')' after parameters")
        body = self._parse_block_statement()

        return FunctionDecl(
            location=SourceLocation(self.filename, start_tok.location.line, start_tok.location.column, start_tok.location.start_offset, body.location.end_offset),
            id=id_tok.value,
            params=params,
            body=body
        )

    def _parse_block_statement(self) -> BlockStmt:
        start_tok = self._consume(TokenType.LBRACE, "Expected '{'")
        statements: List[Statement] = []

        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            if self._match(TokenType.SEMICOLON):
                continue
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)

        end_tok = self._consume(TokenType.RBRACE, "Expected '}' at end of block")
        return BlockStmt(
            location=SourceLocation(self.filename, start_tok.location.line, start_tok.location.column, start_tok.location.start_offset, end_tok.location.end_offset),
            body=statements
        )

    def _parse_if_statement(self) -> IfStmt:
        start_tok = self._consume(TokenType.IF, "Expected 'if'")
        self._consume(TokenType.LPAREN, "Expected '(' after 'if'")
        test_expr = self._parse_expression()
        self._consume(TokenType.RPAREN, "Expected ')' after condition")

        consequent = self._parse_statement()
        alternate: Optional[Statement] = None

        if self._match(TokenType.ELSE):
            alternate = self._parse_statement()

        end_loc = alternate.location if alternate else consequent.location
        return IfStmt(
            location=SourceLocation(self.filename, start_tok.location.line, start_tok.location.column, start_tok.location.start_offset, end_loc.end_offset),
            test=test_expr,
            consequent=consequent,
            alternate=alternate
        )

    def _parse_return_statement(self) -> ReturnStmt:
        start_tok = self._consume(TokenType.RETURN, "Expected 'return'")
        arg: Optional[Expression] = None

        # If next is not semicolon or right brace, parse expression
        if not self._check(TokenType.SEMICOLON) and not self._check(TokenType.RBRACE) and not self._is_at_end():
            arg = self._parse_expression()

        end_loc = arg.location if arg else start_tok.location
        if self._check(TokenType.SEMICOLON):
            end_loc = self._advance().location

        return ReturnStmt(
            location=SourceLocation(self.filename, start_tok.location.line, start_tok.location.column, start_tok.location.start_offset, end_loc.end_offset),
            argument=arg
        )

    def _parse_expression_statement(self) -> ExprStmt:
        expr = self._parse_expression()
        end_loc = expr.location
        if self._check(TokenType.SEMICOLON):
            end_loc = self._advance().location

        return ExprStmt(
            location=SourceLocation(self.filename, expr.location.line, expr.location.column, expr.location.start_offset, end_loc.end_offset),
            expression=expr
        )

    # -------------------------------------------------------------
    # Expression Parsing (Precedence Climbing)
    # -------------------------------------------------------------

    def _parse_expression(self) -> Expression:
        return self._parse_assignment()

    def _parse_assignment(self) -> Expression:
        expr = self._parse_logical_or()

        if self._match(TokenType.EQUAL):
            eq_token = self.tokens[self.pos - 1]
            if not isinstance(expr, Identifier):
                raise CompilerDiagnosticError(Diagnostic(
                    message="Invalid left-hand side in assignment",
                    severity=DiagnosticSeverity.ERROR,
                    location=expr.location,
                    source_code=self.source,
                    suggestion="The left side of an assignment must be a variable identifier"
                ))
            value = self._parse_assignment()
            return AssignmentExpr(
                location=SourceLocation(self.filename, expr.location.line, expr.location.column, expr.location.start_offset, value.location.end_offset),
                left=expr.name,
                right=value
            )

        return expr

    def _parse_logical_or(self) -> Expression:
        expr = self._parse_logical_and()
        while self._match(TokenType.PIPE_PIPE):
            op_token = self.tokens[self.pos - 1]
            right = self._parse_logical_and()
            expr = BinaryExpr(
                location=SourceLocation(self.filename, expr.location.line, expr.location.column, expr.location.start_offset, right.location.end_offset),
                operator=op_token.value,
                left=expr,
                right=right
            )
        return expr

    def _parse_logical_and(self) -> Expression:
        expr = self._parse_equality()
        while self._match(TokenType.AMP_AMP):
            op_token = self.tokens[self.pos - 1]
            right = self._parse_equality()
            expr = BinaryExpr(
                location=SourceLocation(self.filename, expr.location.line, expr.location.column, expr.location.start_offset, right.location.end_offset),
                operator=op_token.value,
                left=expr,
                right=right
            )
        return expr

    def _parse_equality(self) -> Expression:
        expr = self._parse_relational()
        while self._match(TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
            op_token = self.tokens[self.pos - 1]
            right = self._parse_relational()
            expr = BinaryExpr(
                location=SourceLocation(self.filename, expr.location.line, expr.location.column, expr.location.start_offset, right.location.end_offset),
                operator=op_token.value,
                left=expr,
                right=right
            )
        return expr

    def _parse_relational(self) -> Expression:
        expr = self._parse_additive()
        while self._match(TokenType.LESS, TokenType.LESS_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL):
            op_token = self.tokens[self.pos - 1]
            right = self._parse_additive()
            expr = BinaryExpr(
                location=SourceLocation(self.filename, expr.location.line, expr.location.column, expr.location.start_offset, right.location.end_offset),
                operator=op_token.value,
                left=expr,
                right=right
            )
        return expr

    def _parse_additive(self) -> Expression:
        expr = self._parse_multiplicative()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            op_token = self.tokens[self.pos - 1]
            right = self._parse_multiplicative()
            expr = BinaryExpr(
                location=SourceLocation(self.filename, expr.location.line, expr.location.column, expr.location.start_offset, right.location.end_offset),
                operator=op_token.value,
                left=expr,
                right=right
            )
        return expr

    def _parse_multiplicative(self) -> Expression:
        expr = self._parse_unary()
        while self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_token = self.tokens[self.pos - 1]
            right = self._parse_unary()
            expr = BinaryExpr(
                location=SourceLocation(self.filename, expr.location.line, expr.location.column, expr.location.start_offset, right.location.end_offset),
                operator=op_token.value,
                left=expr,
                right=right
            )
        return expr

    def _parse_unary(self) -> Expression:
        if self._match(TokenType.BANG, TokenType.MINUS, TokenType.PLUS):
            op_token = self.tokens[self.pos - 1]
            arg = self._parse_unary()
            return UnaryExpr(
                location=SourceLocation(self.filename, op_token.location.line, op_token.location.column, op_token.location.start_offset, arg.location.end_offset),
                operator=op_token.value,
                argument=arg
            )
        return self._parse_call()

    def _parse_call(self) -> Expression:
        expr = self._parse_primary()

        while True:
            if self._match(TokenType.LPAREN):
                # Call expression
                args: List[Expression] = []
                if not self._check(TokenType.RPAREN):
                    while True:
                        args.append(self._parse_expression())
                        if not self._match(TokenType.COMMA):
                            break
                rparen = self._consume(TokenType.RPAREN, "Expected ')' after call arguments")
                expr = CallExpr(
                    location=SourceLocation(self.filename, expr.location.line, expr.location.column, expr.location.start_offset, rparen.location.end_offset),
                    callee=expr,
                    arguments=args
                )
            else:
                break

        return expr

    def _parse_primary(self) -> Expression:
        tok = self._current()

        if self._match(TokenType.IDENTIFIER):
            return Identifier(location=tok.location, name=tok.value)

        if self._match(TokenType.NUMBER):
            val: Union[int, float] = float(tok.value) if "." in tok.value else int(tok.value)
            return NumberLiteral(location=tok.location, value=val, raw=tok.value)

        if self._match(TokenType.STRING):
            return StringLiteral(location=tok.location, value=tok.value)

        if self._match(TokenType.TRUE):
            return BooleanLiteral(location=tok.location, value=True)

        if self._match(TokenType.FALSE):
            return BooleanLiteral(location=tok.location, value=False)

        if self._match(TokenType.NULL):
            return NullLiteral(location=tok.location)

        if self._match(TokenType.LPAREN):
            expr = self._parse_expression()
            self._consume(TokenType.RPAREN, "Expected ')' to match '('")
            return expr

        raise CompilerDiagnosticError(Diagnostic(
            message=f"Expected expression, found {tok.value!r} ({tok.type.value if isinstance(tok.type.value, str) else tok.type.name})",
            severity=DiagnosticSeverity.ERROR,
            location=tok.location,
            source_code=self.source,
            suggestion="Check syntax or provide a valid expression"
        ))
