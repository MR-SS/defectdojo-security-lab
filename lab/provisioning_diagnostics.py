"""Secret-free stage diagnostics for a separately approved provisioning child."""
import ast


def instrument(source):
    """Annotate statements without executing them; never serialize exception messages."""
    tree = ast.parse(source)

    class Stages(ast.NodeTransformer):
        def visit_With(self, node):
            node.body = self.statements(node.body)
            return node

        def statements(self, body):
            result = []
            for node in body:
                label = f'child-line-{node.lineno}'
                text = ast.unparse(node)
                if not isinstance(node, ast.With):
                    for fragment, name in (
                        ('authorized_users.add', 'assign_scope_membership'),
                        ('objects.create_user', 'create_integration_account'),
                        ('Product_Type.objects.create', 'create_product_type'),
                        ('Token.objects.get_or_create', 'provision_token'),
                    ):
                        if fragment in text:
                            label = name
                marker = ast.parse(f'operation = {label!r}').body[0]
                result.extend([marker, self.visit(node)])
            return result

    tree.body = Stages().statements(tree.body)
    body = ast.unparse(tree)
    return (
        'import json\noperation = "child-start"\ntry:\n'
        + '\n'.join('    ' + line for line in body.splitlines())
        + '\nexcept Exception as exc:\n'
        + '    allowed = {"TypeError", "ValueError", "AssertionError", '
        '"IntegrityError", "OperationalError", "ImportError"}\n'
        + '    kind = type(exc).__name__\n'
        + '    print("DIAGNOSTIC:" + json.dumps({"operation": operation, '
        '"exception_class": kind if kind in allowed else "OtherException", '
        '"category": "provisioning_step_failed", "exit_code": 1, '
        '"rollback": "unverified_requires_readback"}))\n'
        + '    raise SystemExit(1) from None\n'
    )
