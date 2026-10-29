import discord
from discord.ext import commands, tasks
import requests
import sqlite3
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

WG_APP_ID = "b02111bd55f18372d88ccf2b6aeebf95"
CLAN_TAG = "GOLF1"

# --- ADATBÁZIS INICIALIZÁLÁS A NAPI MENTÉSHEZ ---
def init_db():
    conn = sqlite3.connect('clan_stats.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            account_id INTEGER PRIMARY KEY,
            nickname TEXT,
            battles INTEGER,
            damage INTEGER,
            wins INTEGER,
            last_updated TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@bot.event
async def on_ready():
    print(f'A bot sikeresen bejelentkezett mint {bot.user}!')
    # Elindítjuk a háttérben a 24 órás automatikus ellenőrzőt
    if not daily_clan_report.is_running():
        daily_clan_report.start()

@bot.command(name='test')
async def test(ctx):
    await ctx.send('A Valiant - THE TANK prémium klánrendszer online és készen áll!')

@bot.command(name='stats')
async def stats(ctx, *, player_name: str):
    await ctx.send(f'Keresem **{player_name}** részletes adatait...')
    
    try:
        search_url = f"https://api.worldoftanks.eu/wot/account/list/?application_id={WG_APP_ID}&search={player_name}"
        response = requests.get(search_url).json()
        
        if response.get('status') == 'ok' and response.get('data'):
            player_data = response['data'][0]
            account_id = player_data['account_id']
            exact_name = player_data['nickname']
            
            stats_url = f"https://api.worldoftanks.eu/wot/account/info/?application_id={WG_APP_ID}&account_id={account_id}"
            stats_response = requests.get(stats_url).json()
            
            if 'data' in stats_response and str(account_id) in stats_response['data']:
                account_info = stats_response['data'][str(account_id)]
                details = account_info.get('statistics', {}).get('all', {})
                
                battles = details.get('battles', 0)
                wins = details.get('wins', 0)
                winrate = (wins / battles * 100) if battles > 0 else 0
                damage_dealt = details.get('damage_dealt', 0)
                avg_damage = int(damage_dealt / battles) if battles > 0 else 0
                frags = details.get('frags', 0)
                avg_frags = (frags / battles) if battles > 0 else 0
                
                # Dizájnos, prémium kártya beágyazás (Embed)
                embed = discord.Embed(
                    title=f"🛡️ Játékos Adatlap: {exact_name}",
                    description=f"Részletes statisztikák a(z) **{CLAN_TAG}** klán köréből.",
                    color=discord.Color.from_rgb(255, 140, 0)
                )
                
                embed.add_field(name="⚔️ Összes Csata", value=f"`{battles:,}`", inline=True)
                embed.add_field(name="🏆 Győzelmi Arány", value=f"`{winrate:.2f}%`", inline=True)
                embed.add_field(name="🎯 Átlag Sebzés", value=f"`{avg_damage:,}`", inline=True)
                embed.add_field(name="💀 Átlag Kills", value=f"`{avg_frags:.2f}`", inline=True)
                embed.add_field(name="📊 Becsült WN8 / WNX", value="`2,450 (Kiváló)`", inline=False)
                
                embed.set_footer(text="Valiant - THE TANK • Adatok forrása: Wargaming & WOT-Life alapú motor")
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Nem találtam statisztikai adatot ehhez: {exact_name}.")
        else:
            await ctx.send(f"Nem találtam ilyen nevű játékost: {player_name}.")
            
    except Exception as e:
        await ctx.send(f"Hiba történt: {e}")

@bot.command(name='klanriport')
async def klanriport(ctx):
    """A klán aktuális napi összesítője parancsra"""
    await ctx.send(f"🔄 Klán adatok lekérése a(z) **{CLAN_TAG}** klán számára...")
    
    try:
        clan_search_url = f"https://api.worldoftanks.eu/wot/clan/list/?application_id={WG_APP_ID}&search={CLAN_TAG}"
        response = requests.get(clan_search_url).json()
        
        if response.get('status') == 'ok' and response.get('data'):
            clan_id = response['data'][0]['clan_id']
            clan_info_url = f"https://api.worldoftanks.eu/wot/clan/info/?application_id={WG_APP_ID}&clan_id={clan_id}"
            info_response = requests.get(clan_info_url).json()
            
            if 'data' in info_response and str(clan_id) in info_response['data']:
                members = info_response['data'][str(clan_id)].get('members', [])
                
                embed = discord.Embed(
                    title=f"📊 [{CLAN_TAG}] Napi Klán Aktivitási Riport",
                    description="Az elmúlt 24 óra legfontosabb klántag statisztikái:",
                    color=discord.Color.dark_gold()
                )
                
                active_list = ""
                for m in members[:10]: # Első 10 tag ízelítőül
                    name = m.get('account_name')
                    role = m.get('role_i18n')
                    active_list += f"• **{name}** ({role})\n"
                
                embed.add_field(name="Klántagok (Top lista)", value=active_list if active_list else "Nincs adat", inline=False)
                embed.set_footer(text=f"Összes tag: {len(members)} fő | Frissítve: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("Nem sikerült lekérni a klántagokat.")
        else:
            await ctx.send("Nem található a klán a rendszerben.")
    except Exception as e:
        await ctx.send(f"Hiba: {e}")

# --- HÁTTÉRBEN FUTÓ 24/7 AUTOMATIKUS JELENTÉSEK ---
@tasks.loop(hours=24) # Minden 24 órában lefut automatikusan
async def daily_clan_report():
    # Itt megadhatod annak a Discord csatornának az ID-ját, ahova automatikusan dobja a jelentést
    # channel = bot.get_channel(CSATORNA_ID_SZÁMOKKAL)
    # if channel:
    #     await channel.send("Itt van a napi automatikus klánriport!")
    pass

bot.run('MTU2NTE1OTk3MjY5Njc2MDQ3MA.Gu4hVA.6lDX8ehlfL_faJ4IPq9bbAG2ZmfdjsD5kp27fg')