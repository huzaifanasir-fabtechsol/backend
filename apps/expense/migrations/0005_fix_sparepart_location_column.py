from django.db import migrations


def add_location_column_if_missing(apps, schema_editor):
    table_name = "spare_parts"
    connection = schema_editor.connection

    if table_name not in connection.introspection.table_names():
        return

    with connection.cursor() as cursor:
        table_description = connection.introspection.get_table_description(cursor, table_name)
        column_names = {col.name for col in table_description}

    if "location" in column_names:
        return

    schema_editor.execute(
        "ALTER TABLE spare_parts ADD COLUMN location varchar(300) NOT NULL DEFAULT ''"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("expense", "0004_sparepart_expense_spare_part"),
    ]

    operations = [
        migrations.RunPython(add_location_column_if_missing, migrations.RunPython.noop),
    ]

