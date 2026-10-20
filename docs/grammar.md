# Prune Language Grammar Specification

Prune compiles a coherent, well-defined subset of JavaScript/ECMAScript with module support (`.prune` / `.js`).
This grammar is parsed by a handwritten recursive-descent parser.

## 1. Lexical Grammar

```ebnf
Whitespace  ::= [ \t\r\n]+
Comment     ::= SingleLineComment | MultiLineComment
SingleLineComment ::= "//" [^\n]*
MultiLineComment  ::= "/*" ( [^*] | "*"+ [^*/] )* "*"+ "/"

Identifier  ::= [a-zA-Z_$][a-zA-Z0-9_$]*
Number      ::= [0-9]+ ("." [0-9]+)?
String      ::= '"' [^"\\]* '"' | "'" [^'\\]* "'"
Boolean     ::= "true" | "false"
Null        ::= "null"

Keywords    ::= "import" | "export" | "from" | "as"
              | "const" | "let" | "var" | "function"
              | "return" | "if" | "else" | "true" | "false" | "null"

Operators   ::= "+" | "-" | "*" | "/" | "%"
              | "==" | "!=" | "<" | "<=" | ">" | ">="
              | "&&" | "||" | "!" | "="

Punctuation ::= "(" | ")" | "{" | "}" | "[" | "]" | ";" | "," | "."
```

## 2. Syntactic Grammar

```ebnf
Program         ::= Statement* EOF

Statement       ::= ImportDeclaration
                  | ExportDeclaration
                  | VariableDeclaration
                  | FunctionDeclaration
                  | IfStatement
                  | ReturnStatement
                  | BlockStatement
                  | ExpressionStatement
                  | EmptyStatement (";")

ImportDeclaration ::= "import" "{" ImportSpecifierList "}" "from" StringLiteral ";"
ImportSpecifierList ::= ImportSpecifier ("," ImportSpecifier)* ","?
ImportSpecifier   ::= Identifier ("as" Identifier)?

ExportDeclaration ::= "export" (VariableDeclaration | FunctionDeclaration)
                    | "export" "{" ExportSpecifierList "}" ";"
ExportSpecifierList ::= ExportSpecifier ("," ExportSpecifier)* ","?
ExportSpecifier   ::= Identifier ("as" Identifier)?

VariableDeclaration ::= ("const" | "let" | "var") VariableDeclarator ("," VariableDeclarator)* ";"
VariableDeclarator  ::= Identifier ("=" Expression)?

FunctionDeclaration ::= "function" Identifier "(" ParameterList? ")" BlockStatement
ParameterList       ::= Identifier ("," Identifier)*

IfStatement         ::= "if" "(" Expression ")" Statement ("else" Statement)?
ReturnStatement     ::= "return" Expression? ";"
BlockStatement      ::= "{" Statement* "}"
ExpressionStatement ::= Expression ";"

Expression          ::= AssignmentExpression

AssignmentExpression ::= Identifier "=" AssignmentExpression
                       | LogicalOrExpression

LogicalOrExpression  ::= LogicalAndExpression ("||" LogicalAndExpression)*
LogicalAndExpression ::= EqualityExpression ("&&" EqualityExpression)*

EqualityExpression   ::= RelationalExpression (("==" | "!=") RelationalExpression)*
RelationalExpression ::= AdditiveExpression (("<" | "<=" | ">" | ">=") AdditiveExpression)*

AdditiveExpression   ::= MultiplicativeExpression (("+" | "-") MultiplicativeExpression)*
MultiplicativeExpression ::= UnaryExpression (("*" | "/" | "%") UnaryExpression)*

UnaryExpression      ::= ("!" | "-" | "+") UnaryExpression
                       | CallExpression

CallExpression       ::= PrimaryExpression ("(" ArgumentList? ")")*
ArgumentList         ::= Expression ("," Expression)*

PrimaryExpression    ::= Identifier
                       | Number
                       | String
                       | Boolean
                       | Null
                       | "(" Expression ")"
```

## 3. Semantics & Scope Rules
- **Modules**: Each `.prune` file is an independent module with its own lexical scope.
- **Top-Level Bindings**: Declarations at top level are module-scoped unless explicitly exported.
- **Export Granularity**: Prune models dependency edges per export symbol, enabling dead-code elimination at the individual export level rather than whole-file granularity.
- **Top-level Side Effects**: Top-level function calls, variable assignments, and unresolvable operations are treated as side effects and safely preserved in the bundle during module initialization.
