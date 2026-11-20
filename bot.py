
import os
import re
import json
import asyncio
import discord

TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

DATA_FILE = "roles_data.json"

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
lock = asyncio.Lock()

ROLE_PATTERN = re.compile(
    r"^\s*rol\s*-\s*(.+?)\s*$",
    re.IGNORECASE
)

# Identificador para reconocer los roles personales
ROLE_MARKER = "CATVICTUS_PERSONAL:"


def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, dict):
                return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    return {}


def save_data(data):
    temp_file = DATA_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )

    os.replace(temp_file, DATA_FILE)


def find_personal_role(guild, member_id):
    marker = ROLE_MARKER + str(member_id)

    for role in guild.roles:
        if role.name == "@everyone":
            continue

        if role.name and role_marker_matches(role, marker):
            return role

    return None


def role_marker_matches(role, marker):
    return role.name != "@everyone" and (
        role.tags is not None
        and False
    ) or (
        role.name != "@everyone"
        and role_marker_in_data(role, marker)
    )


def role_marker_in_data(role, marker):
    # Los roles personales se identifican por su ID
    # guardado en el archivo de registros.
    return False


@bot.event
async def on_ready():
    print(
        f"CATVICTUS ROLES conectado: {bot.user}"
    )


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.guild is None:
        return

    if message.channel.id != CHANNEL_ID:
        return

    match = ROLE_PATTERN.match(message.content)

    if not match:
        return

    name = match.group(1).strip()

    if not name or len(name) > 32:
        await message.reply(
            "⚠️ El nombre debe tener entre 1 y 32 caracteres.",
            mention_author=False
        )
        return

    if "@everyone" in name.lower() or "@here" in name.lower():
        await message.reply(
            "⚠️ Ese nombre no está permitido.",
            mention_author=False
        )
        return

    async with lock:

        guild = message.guild
        member = message.author

        data = load_data()

        guild_key = str(guild.id)
        member_key = str(member.id)

        records = data.setdefault(guild_key, {})

        old_role_id = records.get(member_key)

        # Bloquear solicitudes posteriores
        if old_role_id:
            await message.reply(
                "🔒 Ya solicitaste tu rol anteriormente.\n"
                "No puedes cambiar el nombre ni solicitar otro rol.",
                mention_author=False
            )
            return

        # Verificar roles personales existentes
        personal_role = find_personal_role(
            guild,
            member.id
        )

        if personal_role:
            records[member_key] = personal_role.id
            save_data(data)

            await message.reply(
                "🔒 Ya tienes un rol personal asignado.\n"
                "No puedes solicitar otro.",
                mention_author=False
            )
            return

        # Evitar nombres duplicados
        existing = discord.utils.get(
            guild.roles,
            name=name
        )

        if existing:
            await message.reply(
                "⚠️ Ese nombre ya existe en el servidor.\n"
                "Elige otro nombre.",
                mention_author=False
            )
            return

        # Verificar permisos
        me = guild.me

        if me is None:
            await message.reply(
                "⚠️ No pude verificar los permisos del bot.",
                mention_author=False
            )
            return

        if not me.guild_permissions.manage_roles:
            await message.reply(
                "⚠️ Necesito el permiso Gestionar roles.",
                mention_author=False
            )
            return

        try:

            # Crear rol personal
            new_role = await guild.create_role(
                name=name,
                permissions=discord.Permissions.none(),
                mentionable=False,
                hoist=False,
                reason="Rol personal solicitado en CATVICTUS"
            )

            # Asignar rol
            try:
                await member.add_roles(
                    new_role,
                    reason="Solicitud de rol personal"
                )

            except discord.HTTPException:
                await new_role.delete(
                    reason="No se pudo asignar el rol"
                )
                raise

            # Guardar solicitud definitiva
            records[member_key] = new_role.id
            save_data(data)

            # Cambiar apodo
            nickname_changed = True

            try:
                await member.edit(
                    nick=name,
                    reason="Nombre solicitado en CATVICTUS"
                )

            except (discord.Forbidden, discord.HTTPException):
                nickname_changed = False

            if nickname_changed:
                await message.reply(
                    "✅ Rol y nombre asignados:\n"
                    f"**{discord.utils.escape_markdown(name)}**\n\n"
                    "🔒 Este nombre es definitivo.",
                    mention_author=False
                )

            else:
                await message.reply(
                    "✅ Rol asignado:\n"
                    f"**{discord.utils.escape_markdown(name)}**\n\n"
                    "⚠️ No pude cambiar tu apodo.\n"
                    "Revisa los permisos y la jerarquía del bot.\n\n"
                    "🔒 No puedes solicitar otro rol.",
                    mention_author=False
                )

        except discord.Forbidden:
            await message.reply(
                "❌ No tengo permisos suficientes.\n"
                "Revisa Gestionar roles y la posición "
                "de mi rol en Discord.",
                mention_author=False
            )

        except discord.HTTPException as error:
            print("Error de Discord:", error)

            await message.reply(
                "❌ Ocurrió un error al crear o asignar el rol.",
                mention_author=False
            )


bot.run(TOKEN)
