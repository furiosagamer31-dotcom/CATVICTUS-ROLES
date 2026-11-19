
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

PATTERN = re.compile(
    r"^\s*rol\s*-\s*(.+?)\s*$",
    re.IGNORECASE
)


def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


@bot.event
async def on_ready():
    print(f"CATVICTUS ROLES conectado: {bot.user}")


@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return

    if message.channel.id != CHANNEL_ID:
        return

    match = PATTERN.fullmatch(message.content)

    if not match:
        return

    name = match.group(1).strip()

    if (
        not name
        or len(name) > 32
        or "\n" in name
        or "\r" in name
        or "@everyone" in name.lower()
        or "@here" in name.lower()
    ):
        await message.reply(
            "❌ Nombre no válido. Usa máximo 32 caracteres.",
            mention_author=False
        )
        return

    async with lock:
        guild = message.guild
        member = message.author

        data = load_data()
        guild_key = str(guild.id)
        records = data.setdefault(guild_key, {})
        member_key = str(member.id)

        old_role_id = records.get(member_key)

        old_role = (
            guild.get_role(old_role_id)
            if old_role_id else None
        )

        try:
            if old_role and old_role.name == name:
                if old_role not in member.roles:
                    await member.add_roles(old_role)

                try:
                    await member.edit(
                        nick=name,
                        reason="Nombre solicitado en CATVICTUS"
                    )
                except discord.Forbidden:
                    pass

                await message.reply(
                    f"✅ Ya tienes asignado el rol: **{discord.utils.escape_markdown(name)}**",
                    mention_author=False
                )
                return

            existing = discord.utils.get(
                guild.roles,
                name=name
            )

            if existing:
                await message.reply(
                    "⚠️ Ese nombre ya existe como rol en el servidor. "
                    "Elige otro nombre o solicita ayuda al staff.",
                    mention_author=False
                )
                return

            new_role = await guild.create_role(
                name=name,
                permissions=discord.Permissions.none(),
                mentionable=False,
                hoist=False,
                reason="Rol personal solicitado en CATVICTUS"
            )

            try:
                await member.add_roles(
                    new_role,
                    reason="Solicitud de rol personal"
                )
            except discord.HTTPException:
                await new_role.delete()
                raise

            records[member_key] = new_role.id
            save_data(data)

            nickname_changed = True

            try:
                await member.edit(
                    nick=name,
                    reason="Nombre solicitado en CATVICTUS"
                )
            except discord.Forbidden:
                nickname_changed = False

            if old_role and old_role in member.roles:
                try:
                    await member.remove_roles(
                        old_role,
                        reason="Cambio de rol personal"
                    )
                except discord.HTTPException:
                    pass

            if nickname_changed:
                await message.reply(
                    "✅ Rol y nombre asignados: **"
                    + discord.utils.escape_markdown(name)
                    + "**",
                    mention_author=False
                )
            else:
                await message.reply(
                    "✅ Rol asignado: **"
                    + discord.utils.escape_markdown(name)
                    + "**\n⚠️ No pude cambiar tu apodo. "
                    "Revisa los permisos y la jerarquía del bot.",
                    mention_author=False
                )

        except discord.Forbidden:
            await message.reply(
                "❌ El bot necesita permisos para gestionar roles "
                "y estar por encima del rol que intenta asignar.",
                mention_author=False
            )

        except discord.HTTPException as error:
            print(f"Error de Discord: {error}")
            await message.reply(
                "❌ Ocurrió un error al procesar tu solicitud.",
                mention_author=False
            )


bot.run(TOKEN)
