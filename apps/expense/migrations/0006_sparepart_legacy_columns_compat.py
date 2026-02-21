from django.db import migrations


def ensure_legacy_columns(apps, schema_editor):
    table_name = "spare_parts"
    connection = schema_editor.connection

    if table_name not in connection.introspection.table_names():
        return

    with connection.cursor() as cursor:
        table_description = connection.introspection.get_table_description(cursor, table_name)
        column_names = {col.name for col in table_description}

    if "part_number" not in column_names:
        schema_editor.execute(
            "ALTER TABLE spare_parts ADD COLUMN part_number varchar(120) NOT NULL DEFAULT ''"
        )

    if "brand" not in column_names:
        schema_editor.execute(
            "ALTER TABLE spare_parts ADD COLUMN brand varchar(120) NOT NULL DEFAULT ''"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("expense", "0005_fix_sparepart_location_column"),
    ]

    operations = [
        migrations.RunPython(ensure_legacy_columns, migrations.RunPython.noop),
    ]

